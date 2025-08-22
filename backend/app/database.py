from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Create database engine
# pool_pre_ping=True helps with connection drops
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.app_env == "development"  # Log SQL queries in dev
)

# Session factory for database operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()

# Dependency to get database session in FastAPI routes
def get_db():
    """
    Database session dependency for FastAPI.
    Ensures sessions are properly closed after each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()