"""
School Result Analysis System - Base Model Registry

This module imports all SQLAlchemy models so that Alembic can discover
them via Base.metadata. Every new model file must be imported here.

This file does NOT define models. It only aggregates imports.
"""

# Import Base so Alembic can access metadata
from app.db.database import Base  # noqa: F401

# ============================================
# All model imports — required for Alembic
# autogenerate to detect tables.
# ============================================
from app.models.user import User  # noqa: F401
from app.models.academic import AcademicYear, ClassLevel, Subject, Exam  # noqa: F401
from app.models.student import Student, StudentEnrollment  # noqa: F401
from app.models.result import StudentResult  # noqa: F401
from app.models.report import HistoricalReport  # noqa: F401
from app.models.import_batch import ImportBatch  # noqa: F401
from app.models.template import ImportTemplate  # noqa: F401
from app.models.app_settings import AppSettings  # noqa: F401
