"""
School Result Analysis System - Database Connection

Configures the SQLAlchemy engine, session factory, and declarative Base.
All models inherit from Base defined here.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings


# Ensure the URL uses the psycopg3 driver dialect.
# Neon and standard PostgreSQL URLs use 'postgresql://' but SQLAlchemy
# needs 'postgresql+psycopg://' to route through psycopg3.
_database_url = settings.DATABASE_URL
if _database_url.startswith("postgresql://"):
    _database_url = _database_url.replace("postgresql://", "postgresql+psycopg://", 1)

# Create the SQLAlchemy engine connected to Neon PostgreSQL.
# pool_pre_ping ensures stale connections are recycled automatically.
engine = create_engine(
    _database_url,
    pool_pre_ping=True,
    echo=False,
)

# Session factory - each call produces a new database session.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """
    Declarative base class for all SQLAlchemy models.
    Every model in /models/ must inherit from this class.
    """

    pass
