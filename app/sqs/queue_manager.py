"""
Módulo gerenciador do Amazon Simple Queue Service (SQS).
Compatível com ambiente local (Ministack) e nuvem (AWS real).
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
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
logger = logging.getLogger("SQSManager")


class SQSQueueManager:
    """Gerenciador completo para operações em filas SQS e Dead Letter Queues (DLQ)."""

    def __init__(
        self,
        queue_name: Optional[str] = None,
        dlq_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region_name: Optional[str] = None,
    ):
        """
        Inicializa o cliente SQS.
        Os parâmetros podem ser passados diretamente ou lidos de variáveis de ambiente.
        """
        self.queue_name = queue_name or os.getenv("SQS_QUEUE_NAME", "sqlarena-submissions-queue")
        self.dlq_name = dlq_name or os.getenv("SQS_DLQ_NAME", f"{self.queue_name}-dlq")
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        
        # Se AWS_ENDPOINT_URL estiver definido (ex: http://localhost:4566), usa local
        self.endpoint_url = endpoint_url or os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")

        # Credenciais (para ambiente local podem ser valores fictícios)
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID", "test")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "test")

        client_kwargs = {
            "region_name": self.region_name,
            "aws_access_key_id": aws_access_key,
            "aws_secret_access_key": aws_secret_key,
        }

        # Só define endpoint_url customizado se não estiver vazio
        if self.endpoint_url:
            client_kwargs["endpoint_url"] = self.endpoint_url

        self.sqs = boto3.client("sqs", **client_kwargs)

        self._queue_url: Optional[str] = None
        self._dlq_url: Optional[str] = None

    # ----------------------------------------------------------------------
    # URLs das Filas
    # ----------------------------------------------------------------------

    def get_queue_url(self) -> str:
        """Obtém a URL da fila principal via API do SQS (com cache em memória)."""
        if not self._queue_url:
            try:
                response = self.sqs.get_queue_url(QueueName=self.queue_name)
                self._queue_url = response["QueueUrl"]
            except ClientError as e:
                logger.error(f"Erro ao obter URL da fila '{self.queue_name}': {e}")
                raise
        return self._queue_url

    def get_dlq_url(self) -> Optional[str]:
        """Obtém a URL da fila Dead Letter Queue (DLQ), se existir."""
        if not self._dlq_url:
            try:
                response = self.sqs.get_queue_url(QueueName=self.dlq_name)
                self._dlq_url = response["QueueUrl"]
            except ClientError:
                # DLQ pode não existir ou não estar configurada
                logger.warning(f"DLQ '{self.dlq_name}' não foi encontrada.")
                return None
        return self._dlq_url

    # ----------------------------------------------------------------------
    # Operações na Fila Principal: Envio (Adicionar)
    # ----------------------------------------------------------------------

    def send_message(
        self,
        payload: Any,
        attributes: Optional[Dict[str, Any]] = None,
        delay_seconds: int = 0,
    ) -> Dict[str, Any]:
        """
        Adiciona uma mensagem à fila principal.
        O payload pode ser um dicionário/lista (serializado automaticamente em JSON) ou string.
        """
        queue_url = self.get_queue_url()

        body = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)

        params: Dict[str, Any] = {
            "QueueUrl": queue_url,
            "MessageBody": body,
            "DelaySeconds": delay_seconds,
        }

        # Formatação de atributos da mensagem (se fornecidos)
        if attributes:
            formatted_attrs = {}
            for key, val in attributes.items():
                if isinstance(val, (int, float)):
                    formatted_attrs[key] = {"DataType": "Number", "StringValue": str(val)}
                else:
                    formatted_attrs[key] = {"DataType": "String", "StringValue": str(val)}
            params["MessageAttributes"] = formatted_attrs

        try:
            response = self.sqs.send_message(**params)
            logger.info(f"Mensagem enviada com sucesso! MessageId: {response.get('MessageId')}")
            return response
        except ClientError as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            raise

    # ----------------------------------------------------------------------
    # Operações na Fila Principal: Leitura e Consumo (Remover)
    # ----------------------------------------------------------------------

    def receive_messages(
        self,
        max_messages: int = 1,
        wait_time_seconds: int = 5,
        visibility_timeout: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Consome mensagens da fila.
        Usa Long Polling por padrão (wait_time_seconds > 0) para reduzir requisições vazias.
        """
        queue_url = self.get_queue_url()

        try:
            response = self.sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=min(max_messages, 10),  # Limite máximo da AWS é 10
                WaitTimeSeconds=wait_time_seconds,
                VisibilityTimeout=visibility_timeout,
                MessageAttributeNames=["All"],
                AttributeNames=["All"],
            )
            messages = response.get("Messages", [])
            logger.info(f"Recebidas {len(messages)} mensagem(ns) da fila principal.")
            return messages
        except ClientError as e:
            logger.error(f"Erro ao receber mensagens: {e}")
            raise

    def delete_message(self, receipt_handle: str) -> bool:
        """
        Remove definitivamente uma mensagem processada da fila usando seu ReceiptHandle.
        """
        queue_url = self.get_queue_url()
        try:
            self.sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle,
            )
            logger.info("Mensagem removida da fila com sucesso.")
            return True
        except ClientError as e:
            logger.error(f"Erro ao deletar mensagem: {e}")
            return False

    # ----------------------------------------------------------------------
    # Limpeza da Fila (Purge)
    # ----------------------------------------------------------------------

    def purge_queue(self) -> bool:
        """
        Limpa (descarta) todas as mensagens presentes na fila principal.
        """
        queue_url = self.get_queue_url()
        try:
            self.sqs.purge_queue(QueueUrl=queue_url)
            logger.info(f"Fila principal '{self.queue_name}' limpa com sucesso.")
            return True
        except ClientError as e:
            logger.error(f"Erro ao limpar fila principal: {e}")
            return False

    # ----------------------------------------------------------------------
    # Operações na Dead Letter Queue (DLQ)
    # ----------------------------------------------------------------------

    def receive_dlq_messages(
        self,
        max_messages: int = 10,
        wait_time_seconds: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Consome mensagens que falharam e caíram na Dead Letter Queue (DLQ).
        """
        dlq_url = self.get_dlq_url()
        if not dlq_url:
            logger.warning("Operação abortada: Nenhuma DLQ configurada.")
            return []

        try:
            response = self.sqs.receive_message(
                QueueUrl=dlq_url,
                MaxNumberOfMessages=min(max_messages, 10),
                WaitTimeSeconds=wait_time_seconds,
                MessageAttributeNames=["All"],
                AttributeNames=["All"],
            )
            messages = response.get("Messages", [])
            logger.info(f"Recebidas {len(messages)} mensagem(ns) da DLQ '{self.dlq_name}'.")
            return messages
        except ClientError as e:
            logger.error(f"Erro ao ler mensagens da DLQ: {e}")
            raise

    def purge_dlq(self) -> bool:
        """
        Limpa (descarta) todas as mensagens presentes na DLQ.
        """
        dlq_url = self.get_dlq_url()
        if not dlq_url:
            return False

        try:
            self.sqs.purge_queue(QueueUrl=dlq_url)
            logger.info(f"DLQ '{self.dlq_name}' limpa com sucesso.")
            return True
        except ClientError as e:
            logger.error(f"Erro ao limpar DLQ: {e}")
            return False

    # ----------------------------------------------------------------------
    # Informações e Estatísticas da Fila
    # ----------------------------------------------------------------------

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas da fila: mensagens disponíveis, mensagens invisíveis (em processamento), etc.
        """
        queue_url = self.get_queue_url()
        try:
            response = self.sqs.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=[
                    "ApproximateNumberOfMessages",
                    "ApproximateNumberOfMessagesNotVisible",
                    "ApproximateNumberOfMessagesDelayed",
                ],
            )
            attrs = response.get("Attributes", {})
            return {
                "mensagens_disponiveis": int(attrs.get("ApproximateNumberOfMessages", 0)),
                "mensagens_em_processamento": int(attrs.get("ApproximateNumberOfMessagesNotVisible", 0)),
                "mensagens_com_delay": int(attrs.get("ApproximateNumberOfMessagesDelayed", 0)),
            }
        except ClientError as e:
            logger.error(f"Erro ao obter estatísticas da fila: {e}")
            return {}
