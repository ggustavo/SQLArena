import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.core.config import settings
from api.core.database import init_db
from api.routes import api_router
from api.services.storage_service import StorageService
from api.services.queue_service import QueueService

logger = logging.getLogger("sqlarena.api")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan managing startup and shutdown routines."""
    logger.info("[Startup] Initializing RDS 1 metadata tables...")
    init_db()
    logger.info("[Startup] RDS 1 tables initialized.")

    logger.info("[Startup] Ensuring AWS resources exist on %s...", settings.AWS_ENDPOINT_URL)
    try:
        StorageService.ensure_bucket_exists()
        QueueService.ensure_queue_exists()
    except Exception as e:
        logger.warning("[Startup] AWS resource initialization notice: %s", e)

    yield
    logger.info("[Shutdown] Application shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Stateless Backend API for Database Teaching & SQL Evaluation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all domain routes
app.include_router(api_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
