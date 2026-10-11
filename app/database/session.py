from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(
    db_url,
    pool_pre_ping=True,
    pool_size=int(getattr(settings, "DB_POOL_SIZE", 5)),
    max_overflow=int(getattr(settings, "DB_MAX_OVERFLOW", 5)),
    pool_recycle=180,
    pool_timeout=int(getattr(settings, "DB_POOL_TIMEOUT", 15)),
    pool_reset_on_return="rollback",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
