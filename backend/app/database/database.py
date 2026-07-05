from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator
from app.core.config import settings

# Create engine with standard configuration options
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create sessionmaker for local db sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Auto-alter to add language_confidence column if not exists (disabled to prevent import-time lock contention)
# from sqlalchemy import text
# try:
#     with engine.begin() as conn:
#         conn.execute(text("ALTER TABLE call ADD COLUMN language_confidence FLOAT"))
# except Exception:
#     pass

def get_db() -> Generator:
    """
    Database session dependency injector.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
