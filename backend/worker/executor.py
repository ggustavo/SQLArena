import logging
from typing import List, Optional, Tuple
import psycopg2
from psycopg2 import errors
from worker.db import DatabaseConnectionFactory

logger = logging.getLogger("sqlarena.worker.executor")


class QueryExecutionResult:
    def __init__(
        self,
        columns: Optional[List[str]] = None,
        rows: Optional[List[Tuple]] = None,
        error: Optional[str] = None,
        is_timeout: bool = False,
    ):
        self.columns = columns or []
        self.rows = rows or []
        self.error = error
        self.is_timeout = is_timeout

    @property
    def is_success(self) -> bool:
        return self.error is None


class QueryExecutor:
    """
    Single-responsibility component for executing SQL queries in RDS 2.
    Enforces DoS protection via statement_timeout, schema isolation, and read-only transactions.
    """

    @classmethod
    def execute(cls, query_sql: str, schema_name: str, timeout_seconds: int) -> QueryExecutionResult:
        conn = None
        timeout_ms = timeout_seconds * 1000

        try:
            conn = DatabaseConnectionFactory.get_rds2_readonly_connection()
            conn.autocommit = False

            with conn.cursor() as cur:
                # 1. DoS statement timeout protection
                cur.execute(f"SET statement_timeout = {timeout_ms};")
                # 2. Schema isolation per question
                cur.execute(f"SET search_path TO {schema_name};")
                # 3. Read-only transaction enforcement
                cur.execute("SET TRANSACTION READ ONLY;")

                cur.execute(query_sql)

                if cur.description:
                    cols = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                else:
                    cols = []
                    rows = []

            conn.commit()
            return QueryExecutionResult(columns=cols, rows=rows)

        except errors.QueryCanceled:
            if conn:
                conn.rollback()
            msg = f"Query timed out after {timeout_seconds} seconds."
            logger.warning("Query timed out in schema %s: %s", schema_name, msg)
            return QueryExecutionResult(error=msg, is_timeout=True)

        except psycopg2.Error as db_err:
            if conn:
                conn.rollback()
            error_msg = getattr(db_err, "pgerror", str(db_err)).strip()
            logger.info("SQL execution error in schema %s: %s", schema_name, error_msg)
            return QueryExecutionResult(error=f"SQL Error: {error_msg}")

        except Exception as exc:
            if conn:
                conn.rollback()
            logger.error("Unexpected execution error in schema %s: %s", schema_name, exc)
            return QueryExecutionResult(error=f"Unexpected error: {str(exc)}")

        finally:
            if conn and not conn.closed:
                conn.close()
