import logging
from botocore.exceptions import ClientError
from api.core.config import settings
from api.services.aws_client import get_boto3_client

logger = logging.getLogger("sqlarena.storage")


class StorageService:
    """Single-responsibility service for managing .sql files in AWS S3."""

    @staticmethod
    def upload_sql_file(content_bytes: bytes, s3_key: str) -> str:
        s3 = get_boto3_client("s3")
        s3.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key,
            Body=content_bytes,
            ContentType="text/plain",
        )
        logger.info("Uploaded S3 object s3://%s/%s (%d bytes)", settings.S3_BUCKET_NAME, s3_key, len(content_bytes))
        return s3_key

    @staticmethod
    def download_sql_file(s3_key: str) -> str:
        s3 = get_boto3_client("s3")
        obj = s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
        return obj["Body"].read().decode("utf-8")

    @staticmethod
    def ensure_bucket_exists() -> None:
        s3 = get_boto3_client("s3")
        try:
            s3.create_bucket(Bucket=settings.S3_BUCKET_NAME)
            logger.info("[S3] Bucket '%s' is ready.", settings.S3_BUCKET_NAME)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code in ["BucketAlreadyOwnedByYou", "BucketAlreadyExists"]:
                logger.info("[S3] Bucket '%s' already exists.", settings.S3_BUCKET_NAME)
            else:
                logger.warning("[S3] Bucket initialization warning: %s", e)
