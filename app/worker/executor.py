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
    Motor de execução em Sandbox PostgreSQL Local (EC2) com auditoria detalhada.
    - Executa 100% no PostgreSQL local da máquina do Worker (desacoplado do RDS).
    - Tabela Hash em memória (RAM) para gabaritos oficiais lidos/gerados a partir do S3.
    - Lazy loading sob demanda de schemas e dados via Amazon S3.
    - Permissões estritas Read-Only e timeout forçado de 3 segundos (3000ms).
    - Serialização canônica e validação por Hash SHA-256 (Strict Mode).
    - Métricas detalhadas de tempo e rastreabilidade para auditoria operacional.
    """

    def __init__(self):
        self.s3 = S3Manager()
        raw_url = settings.SANDBOX_DATABASE_URL or settings.DATABASE_URL
        self.db_url = raw_url.replace("postgresql+psycopg2://", "postgresql://")
        # Normalização preventiva: se contiver localhost, usa 127.0.0.1 para evitar o timeout de 2s IPv6 do Windows
        if "@localhost:" in self.db_url:
            self.db_url = self.db_url.replace("@localhost:", "@127.0.0.1:")

        # Cache em memória RAM dos hashes oficiais de cada questão
        self.cached_hashes: Dict[int, str] = {}

        # Conexão persistente de alta performance mantida com o PostgreSQL local
        self._conn: Optional[Any] = None
        self._retry_attempts = 3
        self._backoff_seconds = 1800  # 30 minutos (1800 segundos)
        self._reconnect_backoff_until = 0.0

    def get_connection(self):
        """
        Retorna a conexão persistente e ativa com o PostgreSQL Sandbox local.
        Aplica política de resiliência estrita:
        - Verifica integridade da conexão atual (não fechada + ping rápido 'SELECT 1;').
        - Em caso de queda, tenta reconectar até 3 vezes imediatamente (com intervalo de 2s).
        - Se as 3 tentativas falharem, entra em backoff de 30 minutos antes de tentar novamente,
          registrando logs detalhados e auditáveis da indisponibilidade.
        """
        now = time.time()

        # 1. Verifica se a conexão existente ainda está saudável
        if self._conn is not None and not self._conn.closed:
            try:
                with self._conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                return self._conn
            except Exception as test_ex:
                logger.warning(
                    f"   [PostgreSQL Sandbox AVISO] Conexão ativa interrompida ({test_ex}). "
                    f"Iniciando ciclo de reconexão..."
                )
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

        # 2. Verifica se está em período de espera pós-falha (backoff de 30 minutos)
        if now < self._reconnect_backoff_until:
            tempo_restante_min = round((self._reconnect_backoff_until - now) / 60, 1)
            msg = (
                f"[PostgreSQL Sandbox ERRO CRÍTICO] Conexão com o banco local bloqueada em backoff. "
                f"Próxima tentativa liberada em {tempo_restante_min} minuto(s)."
            )
            logger.error(msg)
            raise ConnectionError(msg)

        # 3. Política de reconexão: tenta até 3 vezes
        last_error = None
        for tentativa in range(1, self._retry_attempts + 1):
            try:
                logger.info(
                    f"   [PostgreSQL Sandbox] Tentativa de conexão {tentativa}/{self._retry_attempts} "
                    f"com banco local..."
                )
                conn = psycopg2.connect(self.db_url)
                conn.autocommit = True
                self._conn = conn
                self._reconnect_backoff_until = 0.0
                logger.info(
                    f"   ✓ [PostgreSQL Sandbox Conectado] Conexão persistente estabelecida com sucesso "
                    f"na tentativa {tentativa}!"
                )
                return self._conn
            except Exception as conn_err:
                last_error = conn_err
                logger.error(
                    f"   [PostgreSQL Sandbox ERRO] Falha na tentativa {tentativa}/{self._retry_attempts}: {conn_err}"
                )
                if tentativa < self._retry_attempts:
                    time.sleep(2)

        # 4. Falha persistente após 3 tentativas: ativa backoff de 30 minutos
        self._reconnect_backoff_until = now + self._backoff_seconds
        logger.critical(
            f"   🚨 [PostgreSQL Sandbox FALHA PERSISTENTE] Não foi possível conectar ao banco de dados local "
            f"após {self._retry_attempts} tentativas consecutivas. Causa: {last_error}. "
            f"Próxima tentativa de reconexão agendada para daqui a {self._backoff_seconds // 60} minutos."
        )
        raise ConnectionError(
            f"Falha ao conectar com PostgreSQL Sandbox após {self._retry_attempts} tentativas: {last_error}"
        )

    def close(self):
        """Encerra a conexão persistente com o PostgreSQL Sandbox de forma graciosa."""
        if self._conn is not None and not self._conn.closed:
            try:
                self._conn.close()
                logger.info("   [PostgreSQL Sandbox] Conexão persistente encerrada.")
            except Exception:
                pass
            self._conn = None

    def ensure_schema_bootstrapped(self, question_id: int) -> Dict[str, Any]:
        """
        Garante que o schema isolado da questão exista no PostgreSQL local.
        Se não existir, baixa os scripts SQL do S3 sob demanda (Lazy Loading).
        Retorna métricas de tempo da inicialização para auditoria.
        """
        bootstrap_start = time.perf_counter()
        schema_name = f"pergunta_{question_id}"
        conn = self.get_connection()
        metrics = {
            "source": "LOCAL_CACHE",
            "durationMs": 0.0,
            "s3DownloadMs": 0.0,
            "ddlDmlExecutionMs": 0.0,
        }

        try:
            with conn.cursor() as cur:
                # Verifica se o schema já existe no PostgreSQL local
                check_start = time.perf_counter()
                cur.execute(
                    "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s;",
                    (schema_name,)
                )
                exists = cur.fetchone() is not None
                check_ms = (time.perf_counter() - check_start) * 1000

                if exists:
                    # Se o schema já existe mas o hash não está em RAM, carrega o hash
                    if question_id not in self.cached_hashes:
                        logger.info(f"   [RAM Cache Miss] Recuperando hash do gabarito para memória RAM (Questão #{question_id})...")
                        self._load_official_hash_from_s3_and_sandbox(question_id, cur, schema_name)
                    conn.commit()
                    metrics["durationMs"] = round((time.perf_counter() - bootstrap_start) * 1000, 2)
                    logger.info(f"   ✓ [Schema Cache Local] Schema '{schema_name}' verificado no PostgreSQL local em {metrics['durationMs']:.2f} ms.")
                    return metrics

                # Caso não exista localmente: Lazy Loading a partir do Amazon S3
                metrics["source"] = "S3_LAZY_LOAD"
                logger.info(f"   ⬇ [S3 Lazy-Load] Schema '{schema_name}' não encontrado no PostgreSQL local. Baixando scripts do S3...")
                
                s3_start = time.perf_counter()
                files = self.s3.get_question_sql_files(question_id)
                schema_sql = files.get("schema", "")
                data_sql = files.get("data", "")
                answer_sql = files.get("answer", "")
                s3_ms = (time.perf_counter() - s3_start) * 1000
                metrics["s3DownloadMs"] = round(s3_ms, 2)

                logger.info(
                    f"   ✓ [S3 Download Concluído] Scripts baixados em {s3_ms:.2f} ms "
                    f"(schema.sql: {len(schema_sql)} B, data.sql: {len(data_sql)} B, answer.sql: {len(answer_sql)} B)."
                )

                # Cria o schema no PostgreSQL local e popula tabelas e dados
                sql_exec_start = time.perf_counter()
                cur.execute("SET default_transaction_read_only = off;")
                cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {};").format(sql.Identifier(schema_name)))
                cur.execute(sql.SQL("SET search_path TO {}, public;").format(sql.Identifier(schema_name)))

                if schema_sql.strip():
                    cur.execute(schema_sql)
                if data_sql.strip():
                    cur.execute(data_sql)

                sql_ms = (time.perf_counter() - sql_exec_start) * 1000
                metrics["ddlDmlExecutionMs"] = round(sql_ms, 2)
                logger.info(f"   ✓ [DDL/DML Aplicado] Tabelas e registros criados no schema '{schema_name}' em {sql_ms:.2f} ms.")

                # Executa o gabarito oficial para computar e armazenar o hash canônico em memória RAM
                if answer_sql.strip():
                    ans_start = time.perf_counter()
                    cur.execute(answer_sql)
                    cols = [desc[0] for desc in cur.description] if cur.description else []
                    rows = cur.fetchall()
                    official_hash = self.canonical_hash(cols, rows)
                    self.cached_hashes[question_id] = official_hash
                    ans_ms = (time.perf_counter() - ans_start) * 1000
                    logger.info(
                        f"   ✓ [Hash Oficial em RAM] Questão #{question_id} computada em {ans_ms:.2f} ms: "
                        f"{official_hash[:16]}... (Total Hashes em RAM: {len(self.cached_hashes)})"
                    )

                cur.execute("SET default_transaction_read_only = on;")
                conn.commit()
                metrics["durationMs"] = round((time.perf_counter() - bootstrap_start) * 1000, 2)
                logger.info(f"   ✓ [Bootstrap Concluído] Schema '{schema_name}' pronto no PostgreSQL local em {metrics['durationMs']:.2f} ms.")
                return metrics
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise

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
                logger.info(f"   ✓ [RAM Atualizado] Hash oficial #{question_id} carregado em RAM: {official_hash[:16]}...")
        except Exception as e:
            logger.warning(f"   ⚠ Falha ao computar hash oficial para questão #{question_id}: {e}")

    @staticmethod
    def canonical_hash(columns: List[str], rows: List[List[Any]]) -> str:
        """
        Gera o hash SHA-256 canônico determinístico do resultado:
        Serializa nomes de colunas normalizados e valores tipados.
        """
        normalized_data = {
            "columns": [str(c).lower().strip() for c in columns],
            "rows": [[str(val) if val is not None else "NULL" for val in row] for row in rows]
        }
        canonical_str = json.dumps(normalized_data, separators=(',', ':'), ensure_ascii=True)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def get_or_compute_official_hash(self, question_id: int) -> str:
        """Recupera o hash oficial direto da memória RAM do Worker (O(1))."""
        if question_id in self.cached_hashes:
            return self.cached_hashes[question_id]

        self.ensure_schema_bootstrapped(question_id)
        return self.cached_hashes.get(question_id, "")

    def execute_student_query(
        self,
        question_id: int,
        query: str
    ) -> Dict[str, Any]:
        """
        Executa a consulta do aluno em Sandbox seguro com auditoria detalhada:
        - Bloqueia comandos não-SELECT (DDL/DML perigosos).
        - Aplica statement_timeout = 3000ms.
        - Aplica SET TRANSACTION READ ONLY.
        - Cronometra com precisão sub-milissegundo cada etapa.
        - Retorna diagnóstico completo e métricas de auditoria.
        """
        t_total_start = time.perf_counter()
        clean_query = query.strip().rstrip(";")

        audit = {
            "securityCheckMs": 0.0,
            "sandboxSetupMs": 0.0,
            "queryExecutionMs": 0.0,
            "hashEvaluationMs": 0.0,
            "totalExecutorMs": 0.0,
            "rowsCount": 0,
            "columnsCount": 0,
            "sandboxSchema": f"pergunta_{question_id}",
            "officialHash": None,
            "studentHash": None,
        }

        # -------------------------------------------------------------
        # PASSO 1: Análise Estrita de Segurança
        # -------------------------------------------------------------
        t_sec_start = time.perf_counter()
        match = DISALLOWED_REGEX.search(clean_query)
        audit["securityCheckMs"] = round((time.perf_counter() - t_sec_start) * 1000, 2)

        if match:
            forbidden_word = match.group().upper()
            audit["totalExecutorMs"] = round((time.perf_counter() - t_total_start) * 1000, 2)
            logger.warning(
                f"   [PASSO 1/4 - SEGURANÇA BLOQUEADA] Comando não permitido detectado: '{forbidden_word}' "
                f"({audit['securityCheckMs']:.2f} ms). Consulta rejeitada."
            )
            return {
                "outcome": "SYNTAX_ERROR",
                "errorMessage": f"Comando não permitido detectado: '{forbidden_word}'. Apenas consultas de leitura (SELECT) são aceitas.",
                "executionTimeMs": 0.0,
                "columns": [],
                "rows": [],
                "strictModeHashMatched": False,
                "studentHash": None,
                "audit": audit,
            }

        logger.info(f"   [PASSO 1/4 - SEGURANÇA] ✓ Análise léxica concluída em {audit['securityCheckMs']:.2f} ms. Apenas SELECT identificado.")

        # -------------------------------------------------------------
        # PASSO 2: Preparação do Ambiente Sandbox (Schema Isolado)
        # -------------------------------------------------------------
        t_setup_start = time.perf_counter()
        try:
            boot_metrics = self.ensure_schema_bootstrapped(question_id)
            audit["sandboxSetupMs"] = round((time.perf_counter() - t_setup_start) * 1000, 2)
            logger.info(
                f"   [PASSO 2/4 - SANDBOX] ✓ Ambiente 'pergunta_{question_id}' pronto em {audit['sandboxSetupMs']:.2f} ms "
                f"(Origem: {boot_metrics.get('source')})."
            )
        except Exception as e:
            audit["sandboxSetupMs"] = round((time.perf_counter() - t_setup_start) * 1000, 2)
            audit["totalExecutorMs"] = round((time.perf_counter() - t_total_start) * 1000, 2)
            logger.error(f"   [PASSO 2/4 - ERRO SANDBOX] Falha ao preparar ambiente: {e}")
            return {
                "outcome": "SYNTAX_ERROR",
                "errorMessage": f"Erro de infraestrutura ao preparar o ambiente da questão: {e}",
                "executionTimeMs": 0.0,
                "columns": [],
                "rows": [],
                "strictModeHashMatched": False,
                "studentHash": None,
                "audit": audit,
            }

        schema_name = f"pergunta_{question_id}"
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # ---------------------------------------------------------
                # PASSO 3: Configuração de Limites e Execução da Query
                # ---------------------------------------------------------
                cur.execute("SET default_transaction_read_only = on;")
                cur.execute("SET statement_timeout = '3000';")  # Timeout rígido de 3 segundos
                cur.execute(sql.SQL("SET search_path TO {}, public;").format(sql.Identifier(schema_name)))



                logger.info(f"   [PASSO 3/4 - EXECUÇÃO PG] Disparando consulta no PostgreSQL local (Timeout: 3000 ms, Modo: READ ONLY)...")
                t_query_start = time.perf_counter()
                cur.execute(clean_query)
                query_elapsed_ms = round((time.perf_counter() - t_query_start) * 1000, 2)
                audit["queryExecutionMs"] = query_elapsed_ms

                cols = [desc[0] for desc in cur.description] if cur.description else []
                raw_rows = cur.fetchall()
                total_rows = len(raw_rows)
                audit["rowsCount"] = total_rows
                audit["columnsCount"] = len(cols)

                logger.info(
                    f"   [PASSO 3/4 - EXECUÇÃO PG] ✓ Execução concluída em {query_elapsed_ms:.2f} ms. "
                    f"Retornadas {total_rows} linha(s) e {len(cols)} coluna(s): {cols}."
                )

                # Formata até 100 linhas para o frontend
                display_rows = []
                for r in raw_rows[:100]:
                    row_dict = {}
                    for idx, col_name in enumerate(cols):
                        val = r[idx]
                        row_dict[col_name] = str(val) if val is not None else None
                    display_rows.append(row_dict)

                # ---------------------------------------------------------
                # PASSO 4: Avaliação Canônica de Hash (Strict Mode)
                # ---------------------------------------------------------
                t_hash_start = time.perf_counter()
                student_hash = self.canonical_hash(cols, raw_rows)
                official_hash = self.get_or_compute_official_hash(question_id)
                audit["hashEvaluationMs"] = round((time.perf_counter() - t_hash_start) * 1000, 2)
                audit["studentHash"] = student_hash
                audit["officialHash"] = official_hash

                is_match = (student_hash == official_hash)
                outcome = "SUCCESS" if is_match else "WRONG_ANSWER"
                err_msg = None if is_match else "Resultado divergente do gabarito estrito. Verifique ordenação, colunas e valores retornados."
                audit["totalExecutorMs"] = round((time.perf_counter() - t_total_start) * 1000, 2)

                if is_match:
                    logger.info(
                        f"   [PASSO 4/4 - AVALIAÇÃO] 🎉 GABARITO CORRETO! "
                        f"Hash SHA-256 idêntico ao oficial ({student_hash[:16]}...). "
                        f"Tempo total do executor: {audit['totalExecutorMs']:.2f} ms."
                    )
                else:
                    logger.info(
                        f"   [PASSO 4/4 - AVALIAÇÃO] ❌ RESULTADO DIVERGENTE. "
                        f"Hash Aluno: {student_hash[:16]}... != Oficial: {official_hash[:16]}... "
                        f"Tempo total do executor: {audit['totalExecutorMs']:.2f} ms."
                    )

                return {
                    "outcome": outcome,
                    "errorMessage": err_msg,
                    "executionTimeMs": query_elapsed_ms,
                    "columns": cols,
                    "rows": display_rows,
                    "strictModeHashMatched": is_match,
                    "studentHash": student_hash,
                    "audit": audit,
                }

        except psycopg2.errors.QueryCanceled:
            audit["queryExecutionMs"] = 3000.0
            audit["totalExecutorMs"] = round((time.perf_counter() - t_total_start) * 1000, 2)
            logger.warning(f"   [PASSO 3/4 - TIMEOUT] ⏱ Tempo limite excedido (> 3000 ms) na consulta do aluno.")
            return {
                "outcome": "TIMEOUT",
                "errorMessage": "Tempo limite de execução excedido (3 segundos). Verifique se sua consulta contém junções cartesianas ou loops infinitos.",
                "executionTimeMs": 3000.0,
                "columns": [],
                "rows": [],
                "strictModeHashMatched": False,
                "studentHash": None,
                "audit": audit,
            }
        except psycopg2.Error as pg_err:
            audit["totalExecutorMs"] = round((time.perf_counter() - t_total_start) * 1000, 2)
            pg_msg = str(pg_err).strip()
            logger.warning(f"   [PASSO 3/4 - ERRO POSTGRESQL] ⚠ Sintaxe/execução inválida: {pg_msg}")
            return {
                "outcome": "SYNTAX_ERROR",
                "errorMessage": pg_msg,
                "executionTimeMs": 0.0,
                "columns": [],
                "rows": [],
                "strictModeHashMatched": False,
                "studentHash": None,
                "audit": audit,
            }
        except Exception as ex:
            audit["totalExecutorMs"] = round((time.perf_counter() - t_total_start) * 1000, 2)
            logger.error(f"   [PASSO 3/4 - ERRO INESPERADO] ⚠ Exceção: {ex}")
            return {
                "outcome": "SYNTAX_ERROR",
                "errorMessage": str(ex),
                "executionTimeMs": 0.0,
                "columns": [],
                "rows": [],
                "strictModeHashMatched": False,
                "studentHash": None,
                "audit": audit,
            }
        finally:
            try:
                conn.rollback()
            except Exception:
                pass

