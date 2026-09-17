import logging
from typing import Optional
import psycopg2
from api.core.config import settings
from api.core.cache import CacheService
from api.models.question import QuestionStatus
from api.services.storage_service import StorageService

logger = logging.getLogger("sqlarena.provisioner")


class QuestionProvisioner:
    """
    Single-responsibility service executing the teacher question provisioning flow:
    1. Connects to RDS 2 (Execution Database).
    2. Creates isolated schema: question_{question_id}.
    3. Runs DDL and batch DML from S3.
    4. Updates question status to READY in RDS 1.
    5. Invalidates Cache-Aside Redis keys.
    """

    @staticmethod
    def _get_rds2_connection():
        return psycopg2.connect(
            host=settings.RDS2_HOST,
            port=settings.RDS2_PORT,
            user=settings.RDS2_USER,
            password=settings.RDS2_PASSWORD,
            dbname=settings.RDS2_DB,
        )

    @staticmethod
    def _get_rds1_connection():
        return psycopg2.connect(
            host=settings.RDS1_HOST,
            port=settings.RDS1_PORT,
            user=settings.RDS1_USER,
            password=settings.RDS1_PASSWORD,
            dbname=settings.RDS1_DB,
        )

    @classmethod
    def provision_in_rds2(cls, question_id: int, s3_ddl_key: str, s3_dml_key: Optional[str]) -> None:
        schema_name = f"question_{question_id}"
        logger.info("Starting RDS 2 background provisioning for question %d (schema '%s')...", question_id, schema_name)

        rds2_conn = None
        rds1_conn = None

        try:
            # 1. Connect to RDS 2 and execute schema creation + DDL + DML
            rds2_conn = cls._get_rds2_connection()
            rds2_conn.autocommit = False

            with rds2_conn.cursor() as cur:
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name};")
                cur.execute(f"SET search_path TO {schema_name};")

                if s3_ddl_key:
                    logger.info("Fetching DDL from S3: %s", s3_ddl_key)
                    ddl_sql = StorageService.download_sql_file(s3_ddl_key)
                    cur.execute(ddl_sql)
                    logger.info("Executed DDL statements for %s", schema_name)

                if s3_dml_key:
                    logger.info("Fetching DML from S3: %s", s3_dml_key)
                    dml_sql = StorageService.download_sql_file(s3_dml_key)
                    cur.execute(dml_sql)
                    logger.info("Executed DML batch statements for %s", schema_name)

            rds2_conn.commit()
            logger.info("Committed RDS 2 schema '%s'", schema_name)

            # 2. Update Question status to READY in RDS 1
            rds1_conn = cls._get_rds1_connection()
            rds1_conn.autocommit = True
            with rds1_conn.cursor() as cur:
                cur.execute(
                    "UPDATE questions SET status = %s WHERE id = %s;",
                    (QuestionStatus.READY.value, question_id),
                )
            logger.info("Updated Question %d status to 'ready' in RDS 1", question_id)

            # 3. Invalidate Redis Cache-Aside keys
            CacheService.invalidate("cache:questions:catalog", f"cache:question:{question_id}")

        except Exception as exc:
            logger.error("Failed to provision RDS 2 for question %d: %s", question_id, exc, exc_info=True)
            if rds2_conn:
                rds2_conn.rollback()

            try:
                if not rds1_conn or rds1_conn.closed:
                    rds1_conn = cls._get_rds1_connection()
                rds1_conn.autocommit = True
                with rds1_conn.cursor() as cur:
                    cur.execute(
                        "UPDATE questions SET status = %s WHERE id = %s;",
                        (QuestionStatus.ERROR.value, question_id),
                    )
            except Exception as db1_err:
                logger.error("Failed to mark question %d as ERROR in RDS 1: %s", question_id, db1_err)

        finally:
            if rds2_conn and not rds2_conn.closed:
                rds2_conn.close()
            if rds1_conn and not rds1_conn.closed:
                rds1_conn.close()
