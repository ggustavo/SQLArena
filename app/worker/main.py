import json
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import httpx

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app.config import settings
from app.sqs.queue_manager import SQSQueueManager
from app.worker.executor import SandboxExecutor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Worker] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("SubmissionWorker")

class SubmissionWorker:
    """
    Consumidor de Submissões Desacoplado com Auditoria Operacional Completa:
    - 100% isolado do RDS central e do ElastiCache Redis para avaliação.
    - Executa a Sandbox no PostgreSQL local da própria máquina EC2.
    - Rastreabilidade ponta a ponta com cronometragem granular de cada etapa.
    - Notifica a conclusão via HTTP (ALB/Backend) para que o Backend atualize pontuações e caches.
    - Painel de estatísticas de sessão e heartbeat de monitoramento.
    """

    def __init__(self):
        self.sqs = SQSQueueManager()
        self.executor = SandboxExecutor()
        self.running = True
        self.start_time = time.time()
        self.stats = {
            "total": 0,
            "success": 0,
            "wrong_answer": 0,
            "syntax_error": 0,
            "timeout": 0,
            "notified_errors": 0,
        }
        self.empty_poll_counter = 0

    def print_startup_banner(self):
        """Imprime banner de inicialização e diagnóstico do Worker."""
        uptime_start = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        sandbox_url = settings.SANDBOX_DATABASE_URL or settings.DATABASE_URL
        # Mascara credenciais para exibição segura
        safe_db_url = re_mask_url(sandbox_url)

        logger.info("=" * 80)
        logger.info("🚀 SQLArena Submission Worker Iniciado")
        logger.info("-" * 80)
        logger.info(f" • Início:               {uptime_start}")
        logger.info(f" • Fila Amazon SQS:      {self.sqs.queue_name}")
        logger.info(f" • URL da Fila SQS:      {self.sqs.queue_url}")
        logger.info(f" • Bucket Amazon S3:     {settings.S3_BUCKET_NAME}")
        logger.info(f" • PostgreSQL Sandbox:   {safe_db_url}")
        logger.info(f" • Callback Backend:     {settings.BACKEND_INTERNAL_URL}/api/submissions/callback")
        logger.info(f" • Timeout por Consulta: 3000 ms (3 segundos)")
        logger.info(f" • Validação Canônica:   SHA-256 Strict Mode (Tipagem + Ordem Estrita)")
        logger.info("=" * 80)

    def _notify_backend(self, payload: dict) -> tuple[bool, Optional[dict], float]:
        """
        Envia o resultado da submissão para o Backend via HTTP (ALB/API).
        Retorna (sucesso, dados_da_resposta, tempo_em_ms).
        """
        callback_url = f"{settings.BACKEND_INTERNAL_URL.rstrip('/')}/api/submissions/callback"
        if "://localhost:" in callback_url:
            callback_url = callback_url.replace("://localhost:", "://127.0.0.1:")
        headers = {"x-internal-key": settings.INTERNAL_API_KEY}
        t0 = time.perf_counter()

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(callback_url, json=payload, headers=headers)
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                if resp.status_code == 200:
                    data = resp.json()
                    logger.info(
                        f"   [PASSO 5/6 - CALLBACK HTTP] ✓ Backend notificado com sucesso em {latency_ms:.2f} ms "
                        f"(Status: 200 OK | Pontos concedidos: {data.get('pointsAwarded', 0)})."
                    )
                    return True, data, latency_ms
                else:
                    logger.error(f"   [PASSO 5/6 - CALLBACK HTTP ERRO] Status {resp.status_code}: {resp.text} ({latency_ms:.2f} ms)")
                    return False, None, latency_ms
        except Exception as ex:
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.warning(f"   [PASSO 5/6 - CALLBACK HTTP AVISO] Backend inacessível em '{callback_url}' ({ex}). Acionando fallback local...")
            try:
                # Fallback interno para testes unitários onde Uvicorn não está ativo
                from app.api.submissions import process_submission_callback, SubmissionCallbackRequest
                from app.database.session import SessionLocal
                db = SessionLocal()
                try:
                    fb_res = process_submission_callback(
                        SubmissionCallbackRequest(**payload),
                        x_internal_key=settings.INTERNAL_API_KEY,
                        db=db
                    )
                    logger.info(f"   [PASSO 5/6 - FALLBACK LOCAL] ✓ Resultado processado internamente via backend session em {latency_ms:.2f} ms.")
                    return True, fb_res, latency_ms
                finally:
                    db.close()
            except Exception as fallback_err:
                logger.error(f"   [PASSO 5/6 - FALHA CRÍTICA] Erro no fallback backend: {fallback_err}")
                return False, None, latency_ms

    def process_message(self, message: dict) -> bool:
        """Processa uma mensagem de submissão da fila SQS com auditoria detalhada."""
        pipeline_start = time.perf_counter()
        body_raw = message.get("Body", "{}")
        receipt_handle = message.get("ReceiptHandle")
        message_id = message.get("MessageId", "N/A")

        try:
            payload = json.loads(body_raw)
        except Exception as e:
            logger.error(f"❌ [SQS PAYLOAD INVÁLIDO] JSON corrompido: {body_raw[:200]} - Erro: {e}")
            if receipt_handle:
                self.sqs.delete_message(receipt_handle)
            return False

        submission_id = payload.get("submission_id", "sem-id")
        user_id = payload.get("user_id", "anônimo")
        question_id = payload.get("question_id", 0)
        query_sql = (payload.get("query") or "").strip()
        timestamp_sqs = payload.get("timestamp", datetime.now(timezone.utc).isoformat())

        # Formata snippet visual da consulta para o log de auditoria
        query_lines = query_sql.splitlines()
        query_preview = query_lines[0][:100] if query_lines else "(consulta vazia)"
        if len(query_lines) > 1:
            query_preview += f" ... (+{len(query_lines)-1} linhas)"

        logger.info("┌" + "─" * 78 + "┐")
        logger.info(f"│ 📥 [SUBMISSÃO #{submission_id}] Aluno: {user_id} | Questão: #{question_id} | Msg SQS: {message_id[:16]}...")
        logger.info(f"│ 📝 Consulta ({len(query_sql)} caracteres): {query_preview}")
        logger.info("├" + "─" * 78 + "┤")

        # 1. Executa a query no PostgreSQL Local da máquina
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

        # Atualiza estatísticas da sessão
        self.stats["total"] += 1
        if outcome == "SUCCESS":
            self.stats["success"] += 1
        elif outcome == "WRONG_ANSWER":
            self.stats["wrong_answer"] += 1
        elif outcome == "TIMEOUT":
            self.stats["timeout"] += 1
        else:
            self.stats["syntax_error"] += 1

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

        notified, callback_res, cb_time_ms = self._notify_backend(callback_data)

        # 3. Confirmação e descarte na fila SQS
        sqs_del_ms = 0.0
        if receipt_handle and notified:
            t_sqs = time.perf_counter()
            self.sqs.delete_message(receipt_handle)
            sqs_del_ms = round((time.perf_counter() - t_sqs) * 1000, 2)
            logger.info(f"   [PASSO 6/6 - SQS ACK] ✓ Mensagem removida da fila SQS em {sqs_del_ms:.2f} ms.")
        elif not notified:
            self.stats["notified_errors"] += 1
            logger.warning(f"   [PASSO 6/6 - SQS RETRY] Mensagem MANTIDA na fila SQS devido a falha na notificação ao Backend.")

        pipeline_duration_ms = round((time.perf_counter() - pipeline_start) * 1000, 2)
        status_symbol = "✅" if outcome == "SUCCESS" else ("❌" if outcome == "WRONG_ANSWER" else "⚠")

        logger.info("├" + "─" * 78 + "┤")
        logger.info(
            f"│ 🏁 [FINALIZADO] {status_symbol} Status: {outcome} | Duração Total: {pipeline_duration_ms:.2f} ms "
            f"(Query PG: {exec_time:.2f} ms | Callback: {cb_time_ms:.2f} ms | SQS: {sqs_del_ms:.2f} ms)"
        )
        logger.info("└" + "─" * 78 + "┘")

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

    def log_heartbeat(self):
        """Emite log periódico de liveness e status das métricas da sessão."""
        uptime_seconds = int(time.time() - self.start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        cached_count = len(self.executor.cached_hashes)
        logger.info(
            f"[HEARTBEAT] Worker ativo | Fila: '{self.sqs.queue_name}' | "
            f"Processadas: {self.stats['total']} (✅ {self.stats['success']} | "
            f"❌ {self.stats['wrong_answer']} | ⚠ {self.stats['syntax_error']} | "
            f"⏱ {self.stats['timeout']}) | Hashes em RAM: {cached_count} | Uptime: {uptime_str}"
        )

    def run(self, once: bool = False, timeout_seconds: int = 10):
        """Loop principal do Worker."""
        self.print_startup_banner()
        logger.info(f"Worker aguardando submissões na fila '{self.sqs.queue_name}'...")
        deadline = time.time() + timeout_seconds if once else None

        while self.running:
            try:
                messages = self.sqs.receive_messages(
                    max_messages=1,
                    wait_time_seconds=2,
                    visibility_timeout=30
                )
                if messages:
                    self.empty_poll_counter = 0
                    for msg in messages:
                        self.process_message(msg)
                    if once:
                        break
                else:
                    self.empty_poll_counter += 1
                    # A cada ~30 segundos (15 polls de 2s sem mensagem), emite heartbeat de auditoria
                    if self.empty_poll_counter >= 15:
                        self.log_heartbeat()
                        self.empty_poll_counter = 0
                    time.sleep(0.2)

                if once and time.time() > deadline:
                    logger.warning("Tempo limite esgotado em modo 'once' sem mensagens na fila.")
                    break
            except Exception as e:
                logger.error(f"Erro no loop do Worker: {e}")
                time.sleep(2)

        self.print_shutdown_summary()

    def print_shutdown_summary(self):
        """Exibe resumo estatístico no encerramento do worker."""
        uptime = int(time.time() - self.start_time)
        logger.info("=" * 80)
        logger.info("🛑 [ENCERRAMENTO] SQLArena Worker finalizado.")
        logger.info(
            f" • Total de Submissões: {self.stats['total']} "
            f"(Gabarito Correto: {self.stats['success']}, "
            f"Incorretas: {self.stats['wrong_answer']}, "
            f"Erros de Sintaxe: {self.stats['syntax_error']}, "
            f"Timeouts: {self.stats['timeout']})"
        )
        logger.info(f" • Tempo de Atividade: {uptime} segundos")
        logger.info("=" * 80)

def re_mask_url(url: str) -> str:
    """Oculta senha de conexão em URLs para logs seguros."""
    import re
    return re.sub(r":([^@]+)@", r":*****@", url)

def start_worker():
    worker = SubmissionWorker()

    def handle_signal(sig, frame):
        logger.info("\nSinal de parada recebido (SIGINT/SIGTERM). Finalizando ciclos pendentes...")
        worker.running = False

    signal.signal(signal.SIGINT, handle_signal)
    try:
        worker.run()
    finally:
        worker.executor.close()

if __name__ == "__main__":
    start_worker()

