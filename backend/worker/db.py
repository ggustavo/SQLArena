import psycopg2
from worker.config import worker_settings


class DatabaseConnectionFactory:
    """Single-responsibility connection factory for RDS 1 and RDS 2."""

    @staticmethod
    def get_rds1_connection():
        """Connects to RDS 1 (Metadata Database)."""
        return psycopg2.connect(
            host=worker_settings.RDS1_HOST,
            port=worker_settings.RDS1_PORT,
            user=worker_settings.RDS1_USER,
            password=worker_settings.RDS1_PASSWORD,
            dbname=worker_settings.RDS1_DB,
        )

    @staticmethod
    def get_rds2_readonly_connection():
        """
        Connects to RDS 2 (Execution Database) using read-only role credentials if configured,
        or default execution credentials.
        """
        user = worker_settings.RDS2_READONLY_USER or worker_settings.RDS2_USER
        password = worker_settings.RDS2_READONLY_PASSWORD or worker_settings.RDS2_PASSWORD
        return psycopg2.connect(
            host=worker_settings.RDS2_HOST,
            port=worker_settings.RDS2_PORT,
            user=user,
            password=password,
            dbname=worker_settings.RDS2_DB,
        )
