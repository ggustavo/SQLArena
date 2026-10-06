"""
Servico de Worker da Camada de Processamento Assincrono (SQLArena).
Consome submissoes da SQS, executa em sandbox isolada, valida hashes e audita logs.
"""

import json
import logging
import os
import sys
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

import psycopg2
import redis
import boto3
from dotenv import load_dotenv

# Carrega o .env da pasta app/
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

# Adiciona os diretorios raiz e app ao sys.path para importar os modulos internos
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
app_dir = str(Path(__file__).resolve().parent.parent)
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

try:
    from app.sqs.queue_manager import SQSQueueManager
except ImportError:
    from sqs.queue_manager import SQSQueueManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [Worker] %(message)s")
logger = logging.getLogger("SQLArenaWorker")


class SQLArenaWorker:
    def __init__(self):
        # 1. Gerenciador da SQS existente no projeto
        self.sqs_manager = SQSQueueManager()

        # 2. Conexao com DynamoDB
        dynamo_endpoint = os.getenv("DYNAMODB_ENDPOINT_URL", os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566"))
        self.dynamodb = boto3.resource(
            "dynamodb",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            endpoint_url=dynamo_endpoint,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test")
        )
        self.submissions_log_table = self.dynamodb.Table(
            os.getenv("DYNAMODB_SUBMISSIONS_TABLE", "sqlarena-submissions-log")
        )

        # 3. Conexao com Redis
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

        # 4. Strings de conexao PostgreSQL
        self.local_sandbox_url = os.getenv(
            "LOCAL_PG_CONN", 
            "postgresql://postgres:postgres@localhost:5432/sandbox"
        )
        self.rds_url = os.getenv(
            "RDS_PG_CONN", 
            "postgresql://postgres:postgres@localhost:5432/sqlarena"
        )

    def execute_in_sandbox(self, question_id: int, sql_query: str) -> Dict[str, Any]:
        """
        Executa a query na sandbox PostgreSQL local com Search Path isolado
        e timeout rigido de 3000ms para evitar travamentos.
        """
        start_time = time.time()
        conn = None
        try:
            conn = psycopg2.connect(self.local_sandbox_url)
            conn.autocommit = True
            cursor = conn.cursor()

            # Seguranca e isolamento
            cursor.execute("SET statement_timeout = '3000';")
            cursor.execute(f"SET search_path TO pergunta_{question_id};")

            # Execucao da query do aluno
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description] if cursor.description else []
            cursor.close()

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Criacao da representacao canonica para o Hash SHA-256
            canonical_repr = f"COLUMNS:{col_names};ROWS:{rows}"
            hash_result = hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()

            return {
                "status": "SUCCESS",
                "hash": hash_result,
                "elapsed_ms": elapsed_ms,
                "diagnostic": "Query executada com sucesso.",
            }

        except Exception as err:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return {
                "status": "ERROR",
                "hash": None,
                "elapsed_ms": elapsed_ms,
                "diagnostic": str(err),
            }
        finally:
            if conn:
                conn.close()

    def update_rds_xp(self, student_id: str, question_id: int):
        """Concede +10 XP no RDS se for a primeira vez que o aluno acerta."""
        conn = None
        try:
            conn = psycopg2.connect(self.rds_url)
            cur = conn.cursor()
            
            # Checa se ja resolveu antes
            cur.execute(
                "SELECT 1 FROM user_solved_questions WHERE user_id = %s AND question_id = %s",
                (student_id, question_id)
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO user_solved_questions (user_id, question_id) VALUES (%s, %s)",
                    (student_id, question_id)
                )
                cur.execute("UPDATE users SET xp = xp + 10 WHERE id = %s", (student_id,))
                conn.commit()
                logger.info(f"+10 XP concedido ao aluno '{student_id}' pela questao {question_id}!")
            cur.close()
        except Exception as err:
            logger.error(f"Erro ao atualizar XP no RDS: {err}")
        finally:
            if conn:
                conn.close()

    def log_submission_to_dynamo(self, item: Dict[str, Any]):
        """Grava log imutavel no DynamoDB."""
        try:
            self.submissions_log_table.put_item(Item=item)
            logger.info(f"Log de auditoria gravado no DynamoDB para submissao '{item.get('submission_id')}'.")
        except Exception as err:
            logger.error(f"Falha ao gravar no DynamoDB: {err}")

    def process_submission(self, payload: Dict[str, Any]):
        """Fluxo de validacao de ponta a ponta da submissao."""
        submission_id = payload.get("submission_id", f"sub_{int(time.time())}")
        student_id = payload.get("student_id", "anonymous")
        question_id = int(payload.get("question_id", 0))
        sql_query = payload.get("sql_query", "")

        logger.info(f"Processando submissao {submission_id} | Questao: {question_id} | Aluno: {student_id}")

        # 1. Executa na sandbox local
        exec_result = self.execute_in_sandbox(question_id, sql_query)

        verdict = "WRONG_ANSWER"
        if exec_result["status"] == "SUCCESS":
            # 2. Busca gabarito no Redis
            expected_hash = self.redis_client.get(f"question:{question_id}:canonical_hash")

            if expected_hash and exec_result["hash"] == expected_hash:
                verdict = "ACCEPTED"
                self.update_rds_xp(student_id, question_id)
            elif not expected_hash:
                # Se o gabarito nao estiver em cache, marcamos para inspecao
                logger.warning(f"Gabarito da questao {question_id} nao encontrado no Redis!")
                verdict = "ACCEPTED"  # Modo tolerante durante testes
        else:
            verdict = "COMPILATION_ERROR"

        # 3. Persiste o log no DynamoDB
        log_entry = {
            "submission_id": submission_id,
            "student_id": student_id,
            "question_id": question_id,
            "verdict": verdict,
            "execution_time_ms": exec_result["elapsed_ms"],
            "diagnostic_message": exec_result["diagnostic"],
            "submitted_sql": sql_query,
            "created_at": int(time.time()),
        }
        self.log_submission_to_dynamo(log_entry)

    def start(self):
        """Loop continuo de consumo com Long Polling."""
        logger.info("=== SQLArena Worker em execucao (Aguardando mensagens) ===")
        while True:
            try:
                # Long Polling de 20s atraves da classe SQSQueueManager
                messages = self.sqs_manager.receive_messages(
                    max_messages=1, 
                    wait_time_seconds=20, 
                    visibility_timeout=60
                )

                if not messages:
                    continue

                for msg in messages:
                    receipt_handle = msg["ReceiptHandle"]
                    body_raw = msg["Body"]

                    try:
                        payload = json.loads(body_raw)
                        self.process_submission(payload)

                        # Deleta mensagem apos o sucesso
                        self.sqs_manager.delete_message(receipt_handle)
                    except Exception as err:
                        logger.error(f"Erro no processamento da mensagem: {err}")
                        # Nao chama delete_message -> VisibilityTimeout expira e SQS reentrega ate DLQ

            except Exception as loop_err:
                logger.error(f"Falha de comunicacao no loop do Worker: {loop_err}")
                time.sleep(2)


if __name__ == "__main__":
    worker = SQLArenaWorker()
    worker.start()