# Models module - SQLAlchemy ORM models
#
# All models are registered centrally in app/db/base.py
# for Alembic migration discovery.

from app.models.user import User  # noqa: F401
from app.models.academic import AcademicYear, ClassLevel, Subject, Exam  # noqa: F401
from app.models.student import Student, StudentEnrollment  # noqa: F401
from app.models.result import StudentResult  # noqa: F401
from app.models.report import HistoricalReport  # noqa: F401
from app.models.import_batch import ImportBatch  # noqa: F401
from app.models.template import ImportTemplate  # noqa: F401
