import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import boto3
from botocore.exceptions import ClientError
from worker.config import worker_settings
from worker.db import DatabaseConnectionFactory
from worker.executor import QueryExecutor
from worker.validator import ResultValidator
from worker.ddb_logger import DynamoDBSubmissionLogger
from worker.score_service import ScoreConsolidationService

logger = logging.getLogger("sqlarena.worker.consumer")


class SQSSubmissionConsumer:
    """
    Single-responsibility consumer that processes student SQL submissions from SQS:
    1. Reads and parses SQS payload.
    2. Retrieves reference question metadata from RDS 1.
    3. Safely executes reference and student queries in RDS 2 via QueryExecutor.
    4. Evaluates similarity and ORDER BY compliance via ResultValidator.
    5. Logs detailed execution results to DynamoDB via DynamoDBSubmissionLogger.
    6. Updates student's consolidated score in RDS 1 via ScoreConsolidationService.
    7. Acknowledges message from SQS.
    """

    def __init__(self):
        kwargs = {
            "region_name": worker_settings.AWS_REGION,
            "aws_access_key_id": worker_settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": worker_settings.AWS_SECRET_ACCESS_KEY,
        }
        if worker_settings.AWS_ENDPOINT_URL:
            kwargs["endpoint_url"] = worker_settings.AWS_ENDPOINT_URL
        self.sqs = boto3.client("sqs", **kwargs)
        self.queue_url = self._get_queue_url()

    def _get_queue_url(self) -> str:
        try:
            res = self.sqs.get_queue_url(QueueName=worker_settings.SQS_QUEUE_NAME)
            return res["QueueUrl"]
        except ClientError:
            res = self.sqs.create_queue(QueueName=worker_settings.SQS_QUEUE_NAME)
            return res["QueueUrl"]

    def _fetch_question_metadata(self, question_id: int) -> Optional[Dict[str, Any]]:
        conn = None
        try:
            conn = DatabaseConnectionFactory.get_rds1_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, expected_query, timeout_seconds, status FROM questions WHERE id = %s;",
                    (question_id,),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "expected_query": row[1],
                        "timeout_seconds": row[2],
                        "status": row[3],
                    }
        except Exception as e:
            logger.error("Failed to fetch metadata for question %d: %s", question_id, e)
        finally:
            if conn and not conn.closed:
                conn.close()
        return None

    def process_message(self, message_body: str) -> bool:
        try:
            data = json.loads(message_body)
        except Exception as e:
            logger.error("Failed to parse SQS body: %s (%s)", message_body, e)
            return True

        submission_id = data.get("submission_id")
        student_id = data.get("student_id")
        question_id = data.get("question_id")
        submitted_query = data.get("submitted_query", "").strip()
        timestamp = data.get("timestamp", datetime.now(timezone.utc).isoformat())

        logger.info("Evaluating submission %s for student %s on question %s", submission_id, student_id, question_id)

        # 1. Fetch Question metadata
        metadata = self._fetch_question_metadata(question_id)
        if not metadata:
            logger.error("Question %s not found in RDS 1. Acknowledging message.", question_id)
            return True

        expected_query = metadata["expected_query"]
        timeout_seconds = metadata["timeout_seconds"]
        schema_name = f"question_{question_id}"

        # 2. Execute Reference Expected Query in RDS 2
        exp_res = QueryExecutor.execute(expected_query, schema_name, timeout_seconds)
        if not exp_res.is_success:
            logger.error("Reference query failed in schema %s: %s", schema_name, exp_res.error)
            DynamoDBSubmissionLogger.log({
                "submission_id": submission_id,
                "timestamp": timestamp,
                "student_id": student_id,
                "question_id": question_id,
                "submitted_query": submitted_query,
                "status": "ERROR",
                "error_message": f"Reference query failure: {exp_res.error}",
                "score": 0.0,
                "details": {},
            })
            return True

        # 3. Execute Student Query in RDS 2
        stu_res = QueryExecutor.execute(submitted_query, schema_name, timeout_seconds)

        if not stu_res.is_success:
            status_str = "TIMEOUT" if stu_res.is_timeout else "ERROR"
            score = 0.0
            error_message = stu_res.error
            breakdown = {"error": stu_res.error}
        else:
            # 4. Evaluate Result Set Similarity & ORDER BY enforcement
            eval_res = ResultValidator.evaluate(
                expected_cols=exp_res.columns,
                expected_rows=exp_res.rows,
                student_cols=stu_res.columns,
                student_rows=stu_res.rows,
                student_query=submitted_query,
            )
            score = eval_res.score
            status_str = eval_res.status
            error_message = eval_res.error_message
            breakdown = eval_res.breakdown

        # 5. Write log to DynamoDB
        DynamoDBSubmissionLogger.log({
            "submission_id": submission_id,
            "timestamp": timestamp,
            "student_id": student_id,
            "question_id": question_id,
            "submitted_query": submitted_query,
            "status": status_str,
            "error_message": error_message,
            "score": score,
            "details": breakdown,
        })

        # 6. Update student score in RDS 1
        ScoreConsolidationService.update_best_score(
            student_id=student_id,
            question_id=question_id,
            new_score=score,
        )

        return True

    def poll_and_process(self, wait_time_seconds: int = 10, max_messages: int = 5) -> int:
        """Polls SQS for messages and processes each message."""
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time_seconds,
                MessageAttributeNames=["All"],
            )
            messages = response.get("Messages", [])
            for msg in messages:
                receipt_handle = msg.get("ReceiptHandle")
                body = msg.get("Body")

                if self.process_message(body):
                    self.sqs.delete_message(
                        QueueUrl=self.queue_url,
                        ReceiptHandle=receipt_handle,
                    )
            return len(messages)
        except Exception as e:
            logger.error("Error polling SQS queue: %s", e)
            return 0
