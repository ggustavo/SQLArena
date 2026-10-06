import hashlib
import json
import logging
import re
import time
from typing import Dict, Any, List, Optional, Tuple
import psycopg2
from psycopg2 import sql, extras
from app.config import settings
from app.s3.s3_manager import S3Manager
from app.cache.redis_client import redis_client

logger = logging.getLogger("SandboxExecutor")

DISALLOWED_KEYWORDS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
    r"\bCREATE\b", r"\bALTER\b", r"\bTRUNCATE\b", r"\bGRANT\b",
    r"\bREVOKE\b", r"\bEXECUTE\b", r"\bCOPY\b"
]
DISALLOWED_REGEX = re.compile("|".join(DISALLOWED_KEYWORDS), re.IGNORECASE)

class SandboxExecutor:
    """
    Motor de execução em Sandbox PostgreSQL 16.
    - Isolamento de Schemas (pergunta_{id})
    - Bootstrapping automático via S3
    - Permissões Read-Only e timeout estrito de 3 segundos
    - Serialização canônica e validação por Hash SHA-256 (Strict Mode)
    """

    def __init__(self):
        self.s3 = S3Manager()
        self.db_url = settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")

    def _get_connection(self):
        return psycopg2.connect(self.db_url)

    def ensure_schema_bootstrapped(self, question_id: int):
        """Garante que o schema isolado da questão exista e contenha tabelas e dados."""
        schema_name = f"pergunta_{question_id}"
        conn = self._get_connection()
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                # Verifica se o schema já existe
                cur.execute(
                    "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s;",
                    (schema_name,)
                )
                if cur.fetchone():
                    return  # Schema já pronto

                logger.info(f"Bootstrapping do schema '{schema_name}' a partir do S3...")
                
                # Baixa os scripts SQL do S3
                files = self.s3.get_question_sql_files(question_id)
                schema_sql = files.get("schema", "")
                data_sql = files.get("data", "")

                # Cria o schema
                cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {};").format(sql.Identifier(schema_name)))
                cur.execute(sql.SQL("SET search_path TO {}, public;").format(sql.Identifier(schema_name)))

                # Executa DDL e DML
                if schema_sql.strip():
                    cur.execute(schema_sql)
                if data_sql.strip():
                    cur.execute(data_sql)

                logger.info(f"[✓] Schema '{schema_name}' criado e populado com sucesso.")
        finally:
            conn.close()

    @staticmethod
    def canonical_hash(columns: List[str], rows: List[List[Any]]) -> str:
        """
        Gera o hash SHA-256 canônico determinístico do resultado:
        Serializa nomes de colunas ordenados/tipados e linhas ordenadas.
        """
        normalized_data = {
            "columns": [str(c).lower().strip() for c in columns],
            "rows": [[str(val) if val is not None else "NULL" for val in row] for row in rows]
        }
        canonical_str = json.dumps(normalized_data, separators=(',', ':'), ensure_ascii=True)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def get_or_compute_official_hash(self, question_id: int) -> str:
        """Recupera o hash oficial do gabarito no Redis ou computa executando o answer.sql."""
        cached_hash = redis_client.get_answer_hash(question_id)
        if cached_hash:
            return cached_hash

        # Executa o answer.sql para gerar o gabarito
        self.ensure_schema_bootstrapped(question_id)
        schema_name = f"pergunta_{question_id}"
        files = self.s3.get_question_sql_files(question_id)
        answer_sql = files.get("answer", "SELECT 1;")

        conn = self._get_connection()
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("SET search_path TO {}, public;").format(sql.Identifier(schema_name)))
                cur.execute(answer_sql)
                cols = [desc[0] for desc in cur.description] if cur.description else []
                rows = cur.fetchall()
                official_hash = self.canonical_hash(cols, rows)
                redis_client.set_answer_hash(question_id, official_hash)
                return official_hash
        finally:
            conn.close()

    def execute_student_query(
        self,
        question_id: int,
        query: str
    ) -> Dict[str, Any]:
        """
        Executa a consulta do aluno em Sandbox seguro:
        - Bloqueia comandos não-SELECT
        - Aplica statement_timeout = 3000ms
        - Aplica SET TRANSACTION READ ONLY
        - Mede tempo de execução
        - Retorna colunas, linhas, erro (se houver) e status de acerto
        """
        clean_query = query.strip().rstrip(";")

        # 1. Checagem estrita de palavras-chave perigosas (SELECT apenas)
        match = DISALLOWED_REGEX.search(clean_query)
        if match:
            return {
                "outcome": "SYNTAX_ERROR",
                "errorMessage": f"Comando não permitido detectado: '{match.group()}'. Apenas consultas de leitura (SELECT) são aceitas.",
                "executionTimeMs": 0,
                "columns": [],
                "rows": [],
                "strictModeHashMatched": False,
            }

        # 2. Garante bootstrapping do schema
        try:
            self.ensure_schema_bootstrapped(question_id)
        except Exception as e:
            logger.error(f"Erro no bootstrapping do schema para questão #{question_id}: {e}")
            return {
                "outcome": "SYNTAX_ERROR",
                "errorMessage": f"Erro de infraestrutura ao preparar o ambiente da questão: {e}",
                "executionTimeMs": 0,
                "columns": [],
                "rows": [],
                "strictModeHashMatched": False,
            }

        schema_name = f"pergunta_{question_id}"
        conn = self._get_connection()
        try:
            conn.set_session(readonly=True, autocommit=False)
            with conn.cursor() as cur:
                # 3. Restrições de segurança e isolamento
                cur.execute("SET statement_timeout = '3000';")  # 3 segundos
                cur.execute(sql.SQL("SET search_path TO {}, public;").format(sql.Identifier(schema_name)))

                # 4. Execução da query com cronometragem
                start_time = time.perf_counter()
                cur.execute(clean_query)
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

                cols = [desc[0] for desc in cur.description] if cur.description else []
                raw_rows = cur.fetchall()

                # Converte linhas para formatos JSON-serializáveis (máx 100 linhas para o frontend)
                display_rows = []
                for r in raw_rows[:100]:
                    row_dict = {}
                    for idx, col_name in enumerate(cols):
                        val = r[idx]
                        if val is not None:
                            row_dict[col_name] = str(val)
                        else:
                            row_dict[col_name] = None
                    display_rows.append(row_dict)

                # 5. Comparação Canônica com o Gabarito (Strict Mode)
                student_hash = self.canonical_hash(cols, raw_rows)
                official_hash = self.get_or_compute_official_hash(question_id)

                is_match = (student_hash == official_hash)
                outcome = "SUCCESS" if is_match else "WRONG_ANSWER"
                err_msg = None if is_match else "Resultado divergente do gabarito estrito. Verifique ordenação, colunas e valores retornados."

                return {
                    "outcome": outcome,
                    "errorMessage": err_msg,
                    "executionTimeMs": elapsed_ms,
                    "columns": cols,
                    "rows": display_rows,
                    "strictModeHashMatched": is_match,
                    "studentHash": student_hash,
                }

        except psycopg2.errors.QueryCanceled:
            return {
                "outcome": "TIMEOUT",
                "errorMessage": "Tempo limite de execução excedido (3 segundos). Verifique se sua consulta contém junções cartesianas ou loops infinitos.",
                "executionTimeMs": 3000.0,
                "columns": [],
                "rows": [],
                "strictModeHashMatched": False,
            }
        except psycopg2.Error as pg_err:
            # Captura o erro nativo do PostgreSQL para fins de diagnóstico educativo
            pg_msg = str(pg_err).strip()
            return {
                "outcome": "SYNTAX_ERROR",
                "errorMessage": pg_msg,
                "executionTimeMs": 0,
                "columns": [],
                "rows": [],
                "strictModeHashMatched": False,
            }
        except Exception as ex:
            return {
                "outcome": "SYNTAX_ERROR",
                "errorMessage": str(ex),
                "executionTimeMs": 0,
                "columns": [],
                "rows": [],
                "strictModeHashMatched": False,
            }
        finally:
            conn.rollback()
            conn.close()
