"""
Módulo gerenciador do Amazon DynamoDB.
Compatível com ambiente local (Ministack) e nuvem (AWS real).
Responsável pelo registro imutável do histórico detalhado de todas as execuções,
erros do PostgreSQL e resultados das submissões dos alunos.
"""

from datetime import datetime, timezone
from decimal import Decimal
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Carrega variáveis do arquivo central app/.env de forma confiável
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()  # Fallback para o diretório atual de execução

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DynamoDBManager")


def _sanitize_for_dynamodb(data: Any) -> Any:
    """Converte números float para Decimal (requisito estrito do boto3 DynamoDB)."""
    if isinstance(data, float):
        return Decimal(str(data))
    if isinstance(data, dict):
        return {k: _sanitize_for_dynamodb(v) for k, v in data.items() if v is not None}
    if isinstance(data, list):
        return [_sanitize_for_dynamodb(v) for v in data if v is not None]
    return data


class DynamoDBManager:
    """Gerenciador para operações de log imutável de submissões no Amazon DynamoDB."""

    def __init__(
        self,
        table_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region_name: Optional[str] = None,
    ):
        self.table_name = table_name or os.getenv("DYNAMODB_TABLE_NAME", "sqlarena-submissions-log")
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self.endpoint_url = endpoint_url or os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")

        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID", "test")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "test")

        client_kwargs: Dict[str, Any] = {
            "region_name": self.region_name,
            "aws_access_key_id": aws_access_key,
            "aws_secret_access_key": aws_secret_key,
        }

        if self.endpoint_url:
            client_kwargs["endpoint_url"] = self.endpoint_url

        self.client = boto3.client("dynamodb", **client_kwargs)
        self.resource = boto3.resource("dynamodb", **client_kwargs)
        self.table = self.resource.Table(self.table_name)

    # ----------------------------------------------------------------------
    # Gestão da Tabela
    # ----------------------------------------------------------------------

    def ensure_table_exists(self) -> bool:
        """
        Verifica se a tabela existe; caso contrário, cria com chaves e GSI do aluno.
        """
        try:
            self.client.describe_table(TableName=self.table_name)
            logger.info(f"Tabela DynamoDB '{self.table_name}' já existe e está acessível.")
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                logger.info(f"Tabela '{self.table_name}' não encontrada. Criando...")
                try:
                    self.client.create_table(
                        TableName=self.table_name,
                        BillingMode="PAY_PER_REQUEST",
                        KeySchema=[
                            {"AttributeName": "submission_id", "KeyType": "HASH"},
                        ],
                        AttributeDefinitions=[
                            {"AttributeName": "submission_id", "AttributeType": "S"},
                            {"AttributeName": "student_id", "AttributeType": "S"},
                            {"AttributeName": "created_at", "AttributeType": "S"},
                        ],
                        GlobalSecondaryIndexes=[
                            {
                                "IndexName": "StudentIndex",
                                "KeySchema": [
                                    {"AttributeName": "student_id", "KeyType": "HASH"},
                                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                                ],
                                "Projection": {"ProjectionType": "ALL"},
                            }
                        ],
                    )
                    logger.info(f"Tabela '{self.table_name}' criada com sucesso.")
                    return True
                except ClientError as create_err:
                    logger.error(f"Erro ao criar tabela '{self.table_name}': {create_err}")
                    raise
            logger.error(f"Erro ao verificar tabela '{self.table_name}': {e}")
            raise

    # ----------------------------------------------------------------------
    # Gravação e Atualização de Logs de Execução (Ciclo Transacional do Aluno)
    # ----------------------------------------------------------------------

    def save_execution_log(
        self,
        submission_id: Union[str, int],
        student_id: Union[str, int],
        question_id: Union[str, int],
        query: str,
        status: str,
        is_correct: bool = False,
        execution_time_ms: Optional[float] = None,
        pg_error: Optional[str] = None,
        hash_result: Optional[str] = None,
        created_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Grava um registro completo e imutável de execução da submissão no DynamoDB.
        Atende à Seção 8 e 9 dos requisitos:
        "Todas as execuções, acertadas ou não, e os respectivos logs nativos de erro do PostgreSQL...
         são salvas no AWS DynamoDB."
        """
        now_iso = created_at or datetime.now(timezone.utc).isoformat()

        item: Dict[str, Any] = {
            "submission_id": str(submission_id),
            "student_id": str(student_id),
            "question_id": str(question_id),
            "query": query,
            "status": status,  # ex: SUCCESS, WRONG_ANSWER, ERROR, TIMEOUT
            "is_correct": is_correct,
            "created_at": now_iso,
        }

        if execution_time_ms is not None:
            item["execution_time_ms"] = Decimal(str(round(execution_time_ms, 2)))
        if pg_error:
            item["pg_error"] = str(pg_error)
        if hash_result:
            item["hash_result"] = str(hash_result)

        try:
            self.table.put_item(Item=item)
            logger.info(f"Log de submissão #{submission_id} consolidado no DynamoDB.")
            return item
        except ClientError as e:
            logger.error(f"Erro ao salvar log de submissão #{submission_id}: {e}")
            raise

    def update_submission_status(
        self,
        submission_id: Union[str, int],
        status: str,
        is_correct: Optional[bool] = None,
        execution_time_ms: Optional[float] = None,
        pg_error: Optional[str] = None,
        hash_result: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Atualiza o status de uma submissão existente (ex: de PENDING para SUCCESS/ERROR).
        Útil no fluxo assíncrono onde a API registra PENDING e o Worker conclui.
        """
        sub_id = str(submission_id)
        update_expr_parts = ["#st = :status"]
        expr_names = {"#st": "status"}
        expr_values: Dict[str, Any] = {":status": status}

        if is_correct is not None:
            update_expr_parts.append("is_correct = :is_correct")
            expr_values[":is_correct"] = is_correct

        if execution_time_ms is not None:
            update_expr_parts.append("execution_time_ms = :exec_time")
            expr_values[":exec_time"] = Decimal(str(round(execution_time_ms, 2)))

        if pg_error is not None:
            update_expr_parts.append("pg_error = :pg_error")
            expr_values[":pg_error"] = pg_error

        if hash_result is not None:
            update_expr_parts.append("hash_result = :hash_res")
            expr_values[":hash_res"] = hash_result

        update_expr = "SET " + ", ".join(update_expr_parts)

        try:
            response = self.table.update_item(
                Key={"submission_id": sub_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
                ReturnValues="ALL_NEW",
            )
            logger.info(f"Submissão #{submission_id} atualizada com status '{status}'.")
            return response.get("Attributes", {})
        except ClientError as e:
            logger.error(f"Erro ao atualizar submissão #{submission_id}: {e}")
            raise

    # ----------------------------------------------------------------------
    # Consultas e Leitura (Polling do Frontend e Histórico)
    # ----------------------------------------------------------------------

    def get_submission_log(self, submission_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Busca uma submissão pelo submission_id (acesso direto O(1) usado no Polling).
        """
        try:
            response = self.table.get_item(Key={"submission_id": str(submission_id)})
            return response.get("Item")
        except ClientError as e:
            logger.error(f"Erro ao consultar submissão #{submission_id}: {e}")
            raise

    def list_student_submissions(
        self,
        student_id: Union[str, int],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Lista todas as tentativas de um aluno em ordem cronológica decrescente via GSI StudentIndex.
        """
        try:
            response = self.table.query(
                IndexName="StudentIndex",
                KeyConditionExpression="student_id = :sid",
                ExpressionAttributeValues={":sid": str(student_id)},
                ScanIndexForward=False,  # Mais recentes primeiro
                Limit=limit,
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Erro ao listar submissões do aluno #{student_id}: {e}")
            raise

    def list_all_submissions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retorna as submissões mais recentes (Scan limitado, ideal para painel administrativo).
        """
        try:
            response = self.table.scan(Limit=limit)
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Erro ao listar submissões: {e}")
            raise
