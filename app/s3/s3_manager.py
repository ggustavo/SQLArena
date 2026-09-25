"""
Módulo gerenciador do Amazon Simple Storage Service (S3).
Compatível com ambiente local (Ministack) e nuvem (AWS real).
"""

import io
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Carrega variáveis do arquivo central app/.env de forma confiável
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()  # Fallback para o diretório atual de execução

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("S3Manager")


class S3Manager:
    """Gerenciador completo para operações em buckets e objetos S3 no SQLArena."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region_name: Optional[str] = None,
    ):
        """
        Inicializa o cliente S3.
        Os parâmetros podem ser passados diretamente ou lidos de variáveis de ambiente.
        """
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME", "sqlarena-questions-bucket")
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")

        # Se AWS_ENDPOINT_URL estiver definido (ex: http://localhost:4566), usa local
        self.endpoint_url = endpoint_url or os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")

        # Credenciais (para ambiente local podem ser valores fictícios)
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID", "test")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "test")

        client_kwargs: Dict[str, Any] = {
            "region_name": self.region_name,
            "aws_access_key_id": aws_access_key,
            "aws_secret_access_key": aws_secret_key,
        }

        # Configurações para funcionamento transparente com Ministack/LocalStack
        if self.endpoint_url:
            client_kwargs["endpoint_url"] = self.endpoint_url
            # path-style addressing é mandatório para emuladores locais
            client_kwargs["config"] = Config(s3={"addressing_style": "path"})

        self.s3 = boto3.client("s3", **client_kwargs)

    # ----------------------------------------------------------------------
    # Operações de Bucket
    # ----------------------------------------------------------------------

    def ensure_bucket_exists(self) -> bool:
        """
        Verifica se o bucket alvo existe. Caso não exista, cria-o automaticamente.
        """
        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket '{self.bucket_name}' já existe e está acessível.")
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchBucket"):
                logger.info(f"Bucket '{self.bucket_name}' não existe. Criando...")
                try:
                    # 'us-east-1' não aceita CreateBucketConfiguration LocationConstraint
                    if self.region_name == "us-east-1":
                        self.s3.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={"LocationConstraint": self.region_name},
                        )
                    logger.info(f"Bucket '{self.bucket_name}' criado com sucesso.")
                    return True
                except ClientError as create_err:
                    logger.error(f"Erro ao criar bucket '{self.bucket_name}': {create_err}")
                    raise
            else:
                logger.error(f"Erro ao verificar bucket '{self.bucket_name}': {e}")
                raise

    # ----------------------------------------------------------------------
    # Operações Básicas com Objetos
    # ----------------------------------------------------------------------

    def upload_file(
        self,
        key: str,
        content_or_path: Union[str, bytes, Path],
        content_type: str = "text/plain; charset=utf-8",
    ) -> bool:
        """
        Faz upload de conteúdo (string, bytes ou caminho de arquivo local) para o S3.
        """
        key = key.lstrip("/")
        try:
            # Verifica se é um arquivo existente no disco
            is_local_file = False
            if isinstance(content_or_path, Path):
                is_local_file = content_or_path.is_file()
            elif isinstance(content_or_path, str) and "\n" not in content_or_path:
                try:
                    is_local_file = Path(content_or_path).is_file()
                except OSError:
                    is_local_file = False

            if is_local_file:
                path = Path(content_or_path)
                with open(path, "rb") as f:
                    self.s3.put_object(
                        Bucket=self.bucket_name,
                        Key=key,
                        Body=f.read(),
                        ContentType=content_type,
                    )
            elif isinstance(content_or_path, str):
                self.s3.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=content_or_path.encode("utf-8"),
                    ContentType=content_type,
                )
            elif isinstance(content_or_path, bytes):
                self.s3.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=content_or_path,
                    ContentType=content_type,
                )
            else:
                raise ValueError("content_or_path deve ser str, bytes ou Path válido.")

            logger.info(f"Upload concluído: s3://{self.bucket_name}/{key}")
            return True
        except ClientError as e:
            logger.error(f"Erro ao fazer upload para '{key}': {e}")
            raise

    def read_file_text(self, key: str, encoding: str = "utf-8") -> str:
        """
        Lê o conteúdo de um objeto de texto no S3 diretamente para uma string.
        """
        key = key.lstrip("/")
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            body_bytes: bytes = response["Body"].read()
            return body_bytes.decode(encoding)
        except ClientError as e:
            logger.error(f"Erro ao ler objeto '{key}' do bucket '{self.bucket_name}': {e}")
            raise

    def download_file(self, key: str, target_path: Union[str, Path]) -> Path:
        """
        Baixa um objeto do S3 para o sistema de arquivos local.
        Cria pastas pai se necessário.
        """
        key = key.lstrip("/")
        dest = Path(target_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.s3.download_file(self.bucket_name, key, str(dest))
            logger.info(f"Objeto '{key}' baixado com sucesso em '{dest}'.")
            return dest
        except ClientError as e:
            logger.error(f"Erro ao baixar objeto '{key}' para '{target_path}': {e}")
            raise

    def file_exists(self, key: str) -> bool:
        """Verifica se um objeto existe no bucket."""
        key = key.lstrip("/")
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                return False
            logger.error(f"Erro ao consultar objeto '{key}': {e}")
            raise

    def delete_file(self, key: str) -> bool:
        """Remove um objeto do bucket."""
        key = key.lstrip("/")
        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Objeto removido: s3://{self.bucket_name}/{key}")
            return True
        except ClientError as e:
            logger.error(f"Erro ao remover objeto '{key}': {e}")
            return False

    def list_files(self, prefix: str = "") -> List[str]:
        """Lista as chaves de objetos que começam com o prefixo informado."""
        prefix = prefix.lstrip("/")
        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

            keys: List[str] = []
            for page in pages:
                for item in page.get("Contents", []):
                    keys.append(item["Key"])
            return keys
        except ClientError as e:
            logger.error(f"Erro ao listar objetos com prefixo '{prefix}': {e}")
            raise

    # ----------------------------------------------------------------------
    # Operações Específicas do Domínio SQLArena (Questões: schema, data, answer)
    # ----------------------------------------------------------------------

    @staticmethod
    def _question_key_prefix(question_id: Union[int, str]) -> str:
        """Gera o prefixo padronizado para os arquivos de uma questão no S3."""
        return f"questions/{question_id}"

    def upload_question_sql_files(
        self,
        question_id: Union[int, str],
        schema_sql: Union[str, bytes, Path],
        data_sql: Union[str, bytes, Path],
        answer_sql: Union[str, bytes, Path],
    ) -> Dict[str, str]:
        """
        Salva o trio de arquivos de uma questão no S3:
        1. schema.sql (DDL)
        2. data.sql (DML de carga)
        3. answer.sql (Gabarito da consulta)
        """
        prefix = self._question_key_prefix(question_id)
        keys = {
            "schema": f"{prefix}/schema.sql",
            "data": f"{prefix}/data.sql",
            "answer": f"{prefix}/answer.sql",
        }

        self.upload_file(keys["schema"], schema_sql, content_type="text/x-sql; charset=utf-8")
        self.upload_file(keys["data"], data_sql, content_type="text/x-sql; charset=utf-8")
        self.upload_file(keys["answer"], answer_sql, content_type="text/x-sql; charset=utf-8")

        logger.info(f"Arquivos da questão {question_id} salvos no S3 com sucesso.")
        return keys

    def get_question_sql_files(self, question_id: Union[int, str]) -> Dict[str, str]:
        """
        Recupera o conteúdo em texto puro dos 3 arquivos SQL de uma questão:
        retorna dicionário {'schema': str, 'data': str, 'answer': str}.
        """
        prefix = self._question_key_prefix(question_id)
        return {
            "schema": self.read_file_text(f"{prefix}/schema.sql"),
            "data": self.read_file_text(f"{prefix}/data.sql"),
            "answer": self.read_file_text(f"{prefix}/answer.sql"),
        }

    def download_question_sql_files(
        self,
        question_id: Union[int, str],
        target_dir: Union[str, Path],
    ) -> Dict[str, Path]:
        """
        Baixa os 3 arquivos SQL de uma questão para uma pasta local (útil para bootstrapping de workers).
        """
        prefix = self._question_key_prefix(question_id)
        out_dir = Path(target_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        return {
            "schema": self.download_file(f"{prefix}/schema.sql", out_dir / "schema.sql"),
            "data": self.download_file(f"{prefix}/data.sql", out_dir / "data.sql"),
            "answer": self.download_file(f"{prefix}/answer.sql", out_dir / "answer.sql"),
        }

    def delete_question_files(self, question_id: Union[int, str]) -> int:
        """
        Remove todos os arquivos associados a uma questão do S3 (atende à deleção descrita nos requisitos).
        Retorna o número de arquivos removidos.
        """
        prefix = self._question_key_prefix(question_id)
        files = self.list_files(prefix=prefix)
        if not files:
            logger.info(f"Nenhum arquivo encontrado para a questão {question_id} no S3.")
            return 0

        delete_payload = [{"Key": k} for k in files]
        try:
            response = self.s3.delete_objects(
                Bucket=self.bucket_name,
                Delete={"Objects": delete_payload},
            )
            deleted_count = len(response.get("Deleted", []))
            logger.info(f"Removidos {deleted_count} arquivos da questão {question_id} do S3.")
            return deleted_count
        except ClientError as e:
            logger.error(f"Erro ao remover arquivos da questão {question_id}: {e}")
            raise
