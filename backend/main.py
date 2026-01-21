"""FastAPI application entry point."""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.config import settings
from backend.database import init_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    On startup: Initialize database tables.
    """
    # Startup
    logger.info("Starting Finance Analysis API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DATABASE_PATH}")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Finance Analysis API...")


# Create FastAPI application
app = FastAPI(
    title="Finance Analysis API",
    description="AI-powered finance analysis for Brazilian expense tracking",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS for Streamlit frontend
# Dynamic CORS origins from environment variable or fallback to localhost
allowed_origins = []
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    # Production: Use origins from environment variable (comma-separated)
    allowed_origins = [origin.strip() for origin in cors_origins_env.split(",")]
else:
    # Development: Fallback to localhost
    allowed_origins = [
        f"http://localhost:{settings.FRONTEND_PORT}",
        "http://localhost:8501",  # Default Streamlit port
        "http://127.0.0.1:8501",
    ]

logger.info(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.

    Returns API status and configuration info.
    """
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "database": settings.DATABASE_PATH,
    }


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": "Finance Analysis API",
        "version": "0.1.0",
        "description": "AI-powered finance analysis for Brazilian expense tracking",
        "docs": "/docs",
        "health": "/health",
    }


# Import and include API routers
# Note: Import here to avoid circular imports
from backend.api import upload, transactions, subscriptions, reports, categories, income_sources

app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["subscriptions"])
app.include_router(income_sources.router, prefix="/api/income-sources", tags=["income-sources"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])

logger.info("API routers registered successfully")
