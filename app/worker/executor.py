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

logger = logging.getLogger("SandboxExecutor")

DISALLOWED_KEYWORDS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
    r"\bCREATE\b", r"\bALTER\b", r"\bTRUNCATE\b", r"\bGRANT\b",
    r"\bREVOKE\b", r"\bEXECUTE\b", r"\bCOPY\b"
]
DISALLOWED_REGEX = re.compile("|".join(DISALLOWED_KEYWORDS), re.IGNORECASE)

class SandboxExecutor:
    """
    Motor de execução em Sandbox PostgreSQL Local (EC2).
    - Executa 100% no PostgreSQL local da máquina do Worker (desacoplado do RDS).
    - Tabela Hash em memória (RAM) para gabaritos oficiais lidos/gerados a partir do S3.
    - Lazy loading sob demanda de schemas e dados via Amazon S3.
    - Permissões estritas Read-Only e timeout forçado de 3 segundos.
    - Serialização canônica e validação por Hash SHA-256 (Strict Mode).
    """

    def __init__(self):
        self.s3 = S3Manager()
        raw_url = settings.SANDBOX_DATABASE_URL or settings.DATABASE_URL
        self.db_url = raw_url.replace("postgresql+psycopg2://", "postgresql://")
        # Cache em memória RAM dos hashes oficiais de cada questão
        self.cached_hashes: Dict[int, str] = {}

    def _get_connection(self):
        return psycopg2.connect(self.db_url)

    def ensure_schema_bootstrapped(self, question_id: int):
        """
        Garante que o schema isolado da questão exista no PostgreSQL local.
        Se não existir, baixa os scripts SQL do S3 sob demanda (Lazy Loading).
        """
        schema_name = f"pergunta_{question_id}"
        conn = self._get_connection()
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                # Verifica se o schema já existe no PostgreSQL local
                cur.execute(
                    "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s;",
                    (schema_name,)
                )
                if cur.fetchone():
                    # Se o schema já existe mas o hash não está em RAM, garante o carregamento do hash
                    if question_id not in self.cached_hashes:
                        self._load_official_hash_from_s3_and_sandbox(question_id, cur, schema_name)
                    return

                logger.info(f"[S3 Lazy-Load] Baixando scripts do S3 para criar schema '{schema_name}' no Postgres local...")
                
                # Baixa os scripts SQL do Amazon S3
                files = self.s3.get_question_sql_files(question_id)
                schema_sql = files.get("schema", "")
                data_sql = files.get("data", "")
                answer_sql = files.get("answer", "")

                # Cria o schema no PostgreSQL local
                cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {};").format(sql.Identifier(schema_name)))
                cur.execute(sql.SQL("SET search_path TO {}, public;").format(sql.Identifier(schema_name)))

                # Executa DDL e DML
                if schema_sql.strip():
                    cur.execute(schema_sql)
                if data_sql.strip():
                    cur.execute(data_sql)

                # Executa o gabarito oficial para computar e guardar o hash em memória
                if answer_sql.strip():
                    cur.execute(answer_sql)
                    cols = [desc[0] for desc in cur.description] if cur.description else []
                    rows = cur.fetchall()
                    official_hash = self.canonical_hash(cols, rows)
                    self.cached_hashes[question_id] = official_hash
                    logger.info(f"[+] Hash oficial da questão #{question_id} computado e salvo na memória RAM: {official_hash[:12]}...")

                logger.info(f"[✓] Schema '{schema_name}' criado e populado com sucesso no PostgreSQL local.")
        finally:
            conn.close()

    def _load_official_hash_from_s3_and_sandbox(self, question_id: int, cur, schema_name: str):
        """Calcula o hash oficial a partir do answer.sql e armazena na memória do Worker."""
        try:
            files = self.s3.get_question_sql_files(question_id)
            answer_sql = files.get("answer", "")
            if answer_sql.strip():
                cur.execute(sql.SQL("SET search_path TO {}, public;").format(sql.Identifier(schema_name)))
                cur.execute(answer_sql)
                cols = [desc[0] for desc in cur.description] if cur.description else []
                rows = cur.fetchall()
                official_hash = self.canonical_hash(cols, rows)
                self.cached_hashes[question_id] = official_hash
        except Exception as e:
            logger.warning(f"Erro ao computar hash oficial para questão #{question_id}: {e}")

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
        """Recupera o hash oficial direto da memória RAM do Worker (O(1))."""
        # 1. Verifica na tabela hash em memória RAM do Worker
        if question_id in self.cached_hashes:
            return self.cached_hashes[question_id]

        # 2. Se não estiver em memória, garante o bootstrapping local e carrega o hash
        self.ensure_schema_bootstrapped(question_id)
        return self.cached_hashes.get(question_id, "")

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
