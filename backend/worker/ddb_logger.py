import logging
from decimal import Decimal
from typing import Any, Dict
import boto3
from worker.config import worker_settings

logger = logging.getLogger("sqlarena.worker.logger")


class DynamoDBSubmissionLogger:
    """Single-responsibility service for writing immutable execution logs to DynamoDB."""

    @classmethod
    def _get_table(cls):
        kwargs = {
            "region_name": worker_settings.AWS_REGION,
            "aws_access_key_id": worker_settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": worker_settings.AWS_SECRET_ACCESS_KEY,
        }
        if worker_settings.AWS_ENDPOINT_URL:
            kwargs["endpoint_url"] = worker_settings.AWS_ENDPOINT_URL
        dynamodb = boto3.resource("dynamodb", **kwargs)
        return dynamodb.Table(worker_settings.DYNAMODB_TABLE_NAME)

    @classmethod
    def log(cls, log_entry: Dict[str, Any]) -> None:
        table = cls._get_table()

        # Convert float to Decimal for DynamoDB serialization compatibility
        sanitized_item = {}
        for k, v in log_entry.items():
            if isinstance(v, float):
                sanitized_item[k] = Decimal(str(round(v, 2)))
            elif isinstance(v, dict):
                sanitized_item[k] = {
                    sub_k: Decimal(str(round(sub_v, 2))) if isinstance(sub_v, float) else sub_v
                    for sub_k, sub_v in v.items()
                }
            else:
                sanitized_item[k] = v

        table.put_item(Item=sanitized_item)
        logger.info(
            "Logged submission %s [Status: %s, Score: %s] to DynamoDB",
            sanitized_item.get("submission_id"),
            sanitized_item.get("status"),
            sanitized_item.get("score"),
        )
