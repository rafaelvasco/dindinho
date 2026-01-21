"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from pathlib import Path

from backend.config import settings

# Ensure the data directory exists
Path(settings.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=settings.LOG_LEVEL == "DEBUG"  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI endpoints to get database session.

    Yields:
        Session: SQLAlchemy database session

    Example:
        @app.get("/transactions")
        def get_transactions(db: Session = Depends(get_db)):
            return db.query(Transaction).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database by creating all tables and seed initial data.

    This function should be called on application startup.
    It creates all tables defined in models that inherit from Base,
    and seeds the initial categories.
    """
    from backend.models import transaction, subscription, ignored_transaction, category, name_mapping, income_source
    from backend.services.category_service import CategoryService

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Seed initial categories
    db = SessionLocal()
    try:
        category_service = CategoryService(db)
        category_service.seed_initial_categories()
    finally:
        db.close()
