"""
School Result Analysis System - Import Batch Model

Tracks every Excel import operation for auditability.
Each batch records who imported, when, what file, and the outcome.
"""

from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Context ---
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    academic_year_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("academic_years.id"), nullable=False
    )
    class_level_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("class_levels.id"), nullable=False
    )
    exam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exams.id"), nullable=False
    )
    section: Mapped[str] = mapped_column(String(5), nullable=False)

    # --- Audit ---
    uploaded_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # --- Outcome ---
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="completed"
    )  # completed, failed
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # --- Auto-Creation Metrics ---
    students_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    existing_students_matched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enrollments_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- Relationships ---
    academic_year: Mapped["AcademicYear"] = relationship("AcademicYear")
    class_level: Mapped["ClassLevel"] = relationship("ClassLevel")
    exam: Mapped["Exam"] = relationship("Exam")
    uploaded_by_user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<ImportBatch(id={self.id}, file='{self.filename}', "
            f"status='{self.status}', imported={self.imported_rows}/{self.total_rows})>"
        )
