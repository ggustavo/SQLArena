import hashlib
import json
import logging
import re
from typing import Dict, Any, List, Optional
import psycopg2
from psycopg2 import sql
from app.config import settings

logger = logging.getLogger("QuestionValidator")

class QuestionValidationError(Exception):
    """Exceção levantada quando um script de questão falha na validação sandbox."""
    pass

class QuestionValidator:
    """
    Motor de Validação de Questões e Schemas Relacionais no PostgreSQL RDS:
    - Executa em schema isolado (pergunta_{question_id})
    - Valida DDL (schema.sql), DML (data.sql) e gabarito (answer.sql)
    - Exige ORDER BY obrigatório no answer.sql para determinismo estrito
    - Extrai sample_tables e expected_columns automaticamente
    - Gera hash SHA-256 canônico
    - Em caso de falha: executa DROP SCHEMA CASCADE e lança QuestionValidationError
    """

    @staticmethod
    def canonical_hash(columns: List[str], rows: List[List[Any]]) -> str:
        """
        Gera o hash SHA-256 canônico determinístico do resultado:
        Serializa nomes de colunas em minúsculas e valores tipados/nulos.
        """
        normalized_data = {
            "columns": [str(c).lower().strip() for c in columns],
            "rows": [[str(val) if val is not None else "NULL" for val in row] for row in rows]
        }
        canonical_str = json.dumps(normalized_data, separators=(',', ':'), ensure_ascii=True)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @staticmethod
    def validate_and_setup_question(
        question_id: int,
        schema_sql: str,
        data_sql: str,
        answer_sql: str,
    ) -> Dict[str, Any]:
        """
        Valida e prepara o ambiente relacional da questão no PostgreSQL RDS:
        1. Validação estrita de ORDER BY no answer.sql
        2. Criação limpa do schema pergunta_{question_id}
        3. Execução de schema_sql e data_sql
        4. Inspeção das tabelas para extração de sample_tables
        5. Execução do gabarito answer.sql com extração de expected_columns e expected_hash
        6. Se falhar: DROP SCHEMA CASCADE e levanta QuestionValidationError
        """
        clean_answer = (answer_sql or "").strip()
        if not clean_answer:
            raise QuestionValidationError("A consulta gabarito (answer.sql) não pode estar vazia.")

        # Requisito 5: Validação da presença obrigatória de ORDER BY
        if not re.search(r"\bORDER\s+BY\b", clean_answer, re.IGNORECASE):
            raise QuestionValidationError(
                "Erro de Validação (Requisito 5): A consulta gabarito (answer.sql) DEVE conter "
                "cláusula ORDER BY para garantir determinismo no teste de gabarito."
            )

        db_url = settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
        schema_name = f"pergunta_{question_id}"
        conn = None

        try:
            conn = psycopg2.connect(db_url)
            conn.autocommit = True
            with conn.cursor() as cur:
                # 1. Reset limpo do schema sandbox
                cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE;").format(sql.Identifier(schema_name)))
                cur.execute(sql.SQL("CREATE SCHEMA {};").format(sql.Identifier(schema_name)))
                cur.execute(sql.SQL("SET search_path TO {}, public;").format(sql.Identifier(schema_name)))

                # 2. Executa DDL (schema.sql)
                if schema_sql and schema_sql.strip():
                    try:
                        cur.execute(schema_sql)
                    except Exception as err:
                        raise QuestionValidationError(f"Erro na execução do schema.sql (DDL): {err}")

                # 3. Executa DML (data.sql)
                if data_sql and data_sql.strip():
                    try:
                        cur.execute(data_sql)
                    except Exception as err:
                        raise QuestionValidationError(f"Erro na execução do data.sql (DML): {err}")

                # 4. Inspeciona e extrai sample_tables dinamicamente
                sample_tables: List[Dict[str, Any]] = []
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = %s AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """, (schema_name,))
                tables = [r[0] for r in cur.fetchall()]

                for tname in tables:
                    cur.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = %s AND table_name = %s 
                        ORDER BY ordinal_position;
                    """, (schema_name, tname))
                    cols = [r[0] for r in cur.fetchall()]

                    cur.execute(sql.SQL("SELECT * FROM {}.{} LIMIT 5;").format(
                        sql.Identifier(schema_name), sql.Identifier(tname)
                    ))
                    raw_rows = cur.fetchall()
                    rows_list = []
                    for r in raw_rows:
                        row_dict = {}
                        for idx, c in enumerate(cols):
                            val = r[idx]
                            row_dict[c] = str(val) if val is not None else None
                        rows_list.append(row_dict)

                    sample_tables.append({
                        "name": tname,
                        "columns": cols,
                        "rows": rows_list
                    })

                # 5. Executa answer.sql (com timeout de 5 segundos)
                cur.execute("SET statement_timeout = '5000';")
                try:
                    cur.execute(clean_answer)
                except Exception as err:
                    raise QuestionValidationError(f"Erro na execução da consulta gabarito (answer.sql): {err}")

                expected_columns = [desc[0] for desc in cur.description] if cur.description else []
                raw_answer_rows = cur.fetchall()

                # 6. Gera Hash Canônico SHA-256
                expected_hash = QuestionValidator.canonical_hash(expected_columns, raw_answer_rows)
                logger.info(
                    f"[✓] Validação da questão #{question_id} concluída com sucesso. "
                    f"Hash: {expected_hash}, Colunas: {expected_columns}"
                )

                return {
                    "expected_hash": expected_hash,
                    "expected_columns": expected_columns,
                    "sample_tables": sample_tables
                }

        except QuestionValidationError:
            # Dropa o schema em caso de falha de validação
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE;").format(sql.Identifier(schema_name)))
                except Exception:
                    pass
            raise

        except Exception as e:
            # Qualquer outro erro do banco
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE;").format(sql.Identifier(schema_name)))
                except Exception:
                    pass
            raise QuestionValidationError(f"Falha inesperada durante a validação da questão #{question_id}: {e}")

        finally:
            if conn:
                conn.close()

    @staticmethod
    def drop_question_schema(question_id: int):
        """Remove o schema da questão ao ser excluída."""
        schema_name = f"pergunta_{question_id}"
        db_url = settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
        conn = None
        try:
            conn = psycopg2.connect(db_url)
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE;").format(sql.Identifier(schema_name)))
            logger.info(f"[✓] Schema '{schema_name}' removido do banco.")
        except Exception as e:
            logger.warning(f"Erro ao remover schema '{schema_name}': {e}")
            raise
        finally:
            if conn:
                conn.close()
