import json
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app.config import settings
from app.sqs.queue_manager import SQSQueueManager
from app.dynamodb.dynamo_manager import DynamoDBManager
from app.cache.redis_client import redis_client
from app.database.session import SessionLocal
from app.database.models import User, UserSolvedQuestion
from app.worker.executor import SandboxExecutor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [Worker] %(message)s")
logger = logging.getLogger("SubmissionWorker")

class SubmissionWorker:
    def __init__(self):
        self.sqs = SQSQueueManager()
        self.dynamo = DynamoDBManager()
        self.executor = SandboxExecutor()
        self.running = True

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

        # 1. Executa a query no Sandbox PostgreSQL
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

        points_awarded = 0

        # 2. Em caso de acerto inédito: pontua +10 XP no RDS
        if is_correct and user_id:
            db = SessionLocal()
            try:
                solved = db.query(UserSolvedQuestion).filter_by(
                    user_id=user_id,
                    question_id=int(question_id)
                ).first()

                if not solved:
                    db.add(UserSolvedQuestion(user_id=user_id, question_id=int(question_id)))
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        user.score = (user.score or 0) + 10
                        user.solved_count = (user.solved_count or 0) + 1
                    db.commit()
                    points_awarded = 10
                    logger.info(f"[+] +10 pontos concedidos ao usuário '{user_id}'!")
                else:
                    logger.info(f"[*] Questão #{question_id} já havia sido resolvida por '{user_id}'. Sem pontuação duplicada.")
            except Exception as ex:
                db.rollback()
                logger.error(f"Erro ao atualizar pontuação no RDS: {ex}")
            finally:
                db.close()

        # 3. Atualiza status no Redis para polling imediato do frontend
        final_data = {
            "submissionId": submission_id,
            "userId": user_id,
            "questionId": question_id,
            "status": "DONE",
            "outcome": outcome,
            "pointsAwarded": points_awarded,
            "executionTimeMs": exec_time,
            "errorMessage": err_msg,
            "columns": cols,
            "rows": rows,
            "strictModeHashMatched": is_correct,
            "finishedAt": datetime.now(timezone.utc).isoformat(),
        }
        redis_client.set_submission_status(submission_id, final_data)

        # 4. Atualiza registro imutável no DynamoDB
        try:
            self.dynamo.update_submission_result(
                submission_id=submission_id,
                status=outcome,
                is_correct=is_correct,
                execution_time_ms=exec_time,
                error_message=err_msg,
                answer_hash=student_hash
            )
        except Exception as ex:
            logger.warning(f"Erro ao persistir no DynamoDB: {ex}")

        # 5. Remove a mensagem da fila SQS
        if receipt_handle:
            self.sqs.delete_message(receipt_handle)
            logger.info(f"[✓] Submissão #{submission_id} finalizada com status '{outcome}'. Mensagem removida da SQS.")

        return True

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
