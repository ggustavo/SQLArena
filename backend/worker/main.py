import logging
import signal
import sys
import time
from worker.consumer import SQSSubmissionConsumer

logger = logging.getLogger("sqlarena.worker")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

running = True


def handle_termination(signum, frame):
    global running
    logger.info("Termination signal (%s) received. Shutting down worker gracefully...", signum)
    running = False


signal.signal(signal.SIGINT, handle_termination)
signal.signal(signal.SIGTERM, handle_termination)


def main():
    logger.info("Initializing SQLArena Worker...")
    consumer = SQSSubmissionConsumer()
    logger.info("Worker is active and polling SQS for submissions...")

    while running:
        try:
            consumer.poll_and_process(wait_time_seconds=10, max_messages=5)
        except Exception as exc:
            logger.error("Unexpected worker cycle error: %s", exc)
            time.sleep(2)

    logger.info("Worker process terminated cleanly.")


if __name__ == "__main__":
    main()
