"""
School Result Analysis System - Historical Report Model

Stores metadata for uploaded PDF report cards.
Decoupled from the physical storage provider via
storage_provider + storage_key abstraction.
"""

from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class HistoricalReport(Base):
    __tablename__ = "historical_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Foreign Keys ---
    admission_number: Mapped[str] = mapped_column(
        String(20), ForeignKey("students.admission_number"), nullable=False, index=True
    )
    academic_year_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("academic_years.id"), nullable=False
    )
    uploaded_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    # --- Storage Abstraction (provider-agnostic) ---
    storage_provider: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # e.g. "google_drive", "local"
    storage_key: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # e.g. Drive File ID, S3 key, or local path

    # --- Metadata ---
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # --- Constraints ---
    __table_args__ = (
        UniqueConstraint(
            "admission_number", "academic_year_id",
            name="uq_report_student_year"
        ),
    )

    # --- Relationships ---
    student: Mapped["Student"] = relationship("Student", back_populates="historical_reports")
    academic_year: Mapped["AcademicYear"] = relationship(
        "AcademicYear", back_populates="historical_reports"
    )
    uploaded_by_user: Mapped["User"] = relationship("User", back_populates="uploaded_reports")

    def __repr__(self) -> str:
        return (
            f"<HistoricalReport(id={self.id}, adm='{self.admission_number}', "
            f"year_id={self.academic_year_id}, file='{self.original_filename}')>"
        )
