import logging
from datetime import datetime, timezone
from worker.db import DatabaseConnectionFactory

logger = logging.getLogger("sqlarena.worker.score")


class ScoreConsolidationService:
    """Single-responsibility service for updating consolidated student scores in RDS 1."""

    @classmethod
    def update_best_score(cls, student_id: int, question_id: int, new_score: float) -> None:
        conn = None
        try:
            conn = DatabaseConnectionFactory.get_rds1_connection()
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, best_score FROM student_scores WHERE student_id = %s AND question_id = %s;",
                    (student_id, question_id),
                )
                row = cur.fetchone()
                now = datetime.now(timezone.utc)

                if row:
                    score_id, current_best = row[0], row[1]
                    if new_score > current_best:
                        cur.execute(
                            "UPDATE student_scores SET best_score = %s, updated_at = %s WHERE id = %s;",
                            (new_score, now, score_id),
                        )
                        logger.info("Updated best score for student %d on Q%d: %.2f -> %.2f",
                                    student_id, question_id, current_best, new_score)
                    else:
                        logger.info("Score %.2f is not higher than best %.2f for student %d on Q%d",
                                    new_score, current_best, student_id, question_id)
                else:
                    cur.execute(
                        "INSERT INTO student_scores (student_id, question_id, best_score, updated_at) VALUES (%s, %s, %s, %s);",
                        (student_id, question_id, new_score, now),
                    )
                    logger.info("Inserted new initial score for student %d on Q%d: %.2f",
                                student_id, question_id, new_score)

        except Exception as e:
            logger.error("Failed to update consolidated score in RDS 1: %s", e)
        finally:
            if conn and not conn.closed:
                conn.close()
