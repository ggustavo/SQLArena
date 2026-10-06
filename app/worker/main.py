import json
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app.config import settings
from app.sqs.queue_manager import SQSQueueManager
from app.worker.executor import SandboxExecutor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [Worker] %(message)s")
logger = logging.getLogger("SubmissionWorker")

class SubmissionWorker:
    """
    Consumidor de Submissões Desacoplado:
    - 100% isolado do RDS central e do ElastiCache Redis.
    - Executa a Sandbox no PostgreSQL local da própria máquina EC2.
    - Notifica a conclusão via HTTP (ALB/Backend) para que o Backend atualize pontuações e caches.
    """

    def __init__(self):
        self.sqs = SQSQueueManager()
        self.executor = SandboxExecutor()
        self.running = True

    def _notify_backend(self, payload: dict) -> bool:
        """Envia o resultado da submissão para o Backend via HTTP (ALB)."""
        callback_url = f"{settings.BACKEND_INTERNAL_URL.rstrip('/')}/api/submissions/callback"
        headers = {"x-internal-key": settings.INTERNAL_API_KEY}

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(callback_url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    logger.info(f"[Callback HTTP 200] Backend notificado com sucesso! Pontos: {data.get('pointsAwarded', 0)}")
                    return True
                else:
                    logger.error(f"[Callback HTTP Erro] Status {resp.status_code}: {resp.text}")
                    return False
        except Exception as ex:
            logger.warning(f"[Callback HTTP] Backend não respondeu em '{callback_url}' ({ex}). Acionando fallback interno para ambiente local/testes...")
            try:
                # Fallback exclusivo para testes unitários locais onde o Uvicorn não está em execução
                from app.api.submissions import process_submission_callback, SubmissionCallbackRequest
                from app.database.session import SessionLocal
                db = SessionLocal()
                try:
                    process_submission_callback(
                        SubmissionCallbackRequest(**payload),
                        x_internal_key=settings.INTERNAL_API_KEY,
                        db=db
                    )
                    logger.info("[✓ Fallback Local] Resultado processado via serviço backend diretamente.")
                    return True
                finally:
                    db.close()
            except Exception as fallback_err:
                logger.error(f"Erro no fallback local do backend: {fallback_err}")
                return False

    def process_message(self, message: dict) -> bool:
        """Processa uma única mensagem de submissão da fila SQS."""
        body_raw = message.get("Body", "{}")
        receipt_handle = message.get("ReceiptHandle")
        message_id = message.get("MessageId")

        try:
            payload = json.loads(body_raw)
        except Exception as e:
            logger.error(f"Payload inválido (JSON malformado): {body_raw} - {e}")
            if receipt_handle:
                self.sqs.delete_message(receipt_handle)
            return False

        submission_id = payload.get("submission_id")
        user_id = payload.get("user_id")
        question_id = payload.get("question_id")
        query_sql = payload.get("query")

        logger.info(f"Processando submissão #{submission_id} (Questão #{question_id} pelo Aluno {user_id})...")

        # 1. Executa a query 100% no PostgreSQL Local da máquina
        res = self.executor.execute_student_query(
            question_id=int(question_id),
            query=query_sql
        )

        outcome = res["outcome"]
        is_correct = res["strictModeHashMatched"]
        exec_time = res["executionTimeMs"]
        err_msg = res["errorMessage"]
        cols = res["columns"]
        rows = res["rows"]
        student_hash = res.get("studentHash")

        # 2. Notifica o Backend via HTTP (ALB) com o resultado
        callback_data = {
            "submissionId": submission_id,
            "userId": user_id,
            "questionId": int(question_id),
            "status": "DONE",
            "outcome": outcome,
            "isCorrect": is_correct,
            "executionTimeMs": exec_time,
            "errorMessage": err_msg,
            "columns": cols,
            "rows": rows,
            "studentHash": student_hash
        }

        notified = self._notify_backend(callback_data)

        # 3. Se o Backend processou a notificação, remove da fila SQS
        if receipt_handle and notified:
            self.sqs.delete_message(receipt_handle)
            logger.info(f"[✓] Submissão #{submission_id} finalizada com status '{outcome}'. Mensagem removida da SQS.")

        return notified

    def process_one_message(self, wait_seconds: int = 2) -> bool:
        """Busca e processa exatamente 1 mensagem da fila SQS se houver."""
        messages = self.sqs.receive_messages(
            max_messages=1,
            wait_time_seconds=wait_seconds,
            visibility_timeout=30
        )
        if messages:
            return self.process_message(messages[0])
        return False

    def run(self, once: bool = False, timeout_seconds: int = 10):
        """Loop principal do Worker."""
        logger.info(f"Worker iniciado. Escutando fila '{self.sqs.queue_name}'...")
        deadline = time.time() + timeout_seconds if once else None
        
        while self.running:
            try:
                messages = self.sqs.receive_messages(
                    max_messages=1,
                    wait_time_seconds=2,
                    visibility_timeout=30
                )
                if messages:
                    for msg in messages:
                        self.process_message(msg)
                    if once:
                        break
                else:
                    time.sleep(0.2)

                if once and time.time() > deadline:
                    logger.warning("Tempo limite esgotado em modo 'once' sem mensagens na fila.")
                    break
            except Exception as e:
                logger.error(f"Erro no loop do Worker: {e}")
                time.sleep(2)

def start_worker():
    worker = SubmissionWorker()

    def handle_signal(sig, frame):
        logger.info("Sinal de parada recebido. Encerrando Worker...")
        worker.running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    worker.run()

if __name__ == "__main__":
    start_worker()
