import json
import logging
from botocore.exceptions import ClientError
from api.core.config import settings
from api.services.aws_client import get_boto3_client

logger = logging.getLogger("sqlarena.queue")


class QueueService:
    """Single-responsibility service for publishing messages to AWS SQS."""

    @classmethod
    def get_or_create_queue_url(cls) -> str:
        sqs = get_boto3_client("sqs")
        try:
            res = sqs.get_queue_url(QueueName=settings.SQS_QUEUE_NAME)
            return res["QueueUrl"]
        except ClientError:
            res = sqs.create_queue(QueueName=settings.SQS_QUEUE_NAME)
            return res["QueueUrl"]

    @classmethod
    def publish_submission(cls, payload: dict) -> str:
        sqs = get_boto3_client("sqs")
        queue_url = cls.get_or_create_queue_url()
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(payload),
            MessageAttributes={
                "SubmissionId": {"DataType": "String", "StringValue": str(payload.get("submission_id"))},
                "StudentId": {"DataType": "Number", "StringValue": str(payload.get("student_id"))},
                "QuestionId": {"DataType": "Number", "StringValue": str(payload.get("question_id"))},
            },
        )
        logger.info("Published submission %s to SQS queue %s", payload.get("submission_id"), queue_url)
        return response.get("MessageId")

    @classmethod
    def ensure_queue_exists(cls) -> None:
        cls.get_or_create_queue_url()
