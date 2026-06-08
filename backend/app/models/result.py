"""
School Result Analysis System - Student Result Model

Normalized result storage linking a student's enrollment
to a specific subject and exam with marks/grade data.
"""

from sqlalchemy import Integer, Float, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class StudentResult(Base):
    __tablename__ = "student_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Foreign Keys ---
    student_enrollment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("student_enrollments.id"), nullable=False, index=True
    )
    subject_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subjects.id"), nullable=False
    )
    exam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exams.id"), nullable=False
    )

    # --- Result Data ---
    marks_obtained: Mapped[float | None] = mapped_column(Float, nullable=True)  # Can be null if only grade is given
    max_marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(5), nullable=True)  # e.g. "A1", "B2", "AB" (absent)

    # --- Constraints ---
    # A student cannot have duplicate results for the same subject + exam
    __table_args__ = (
        UniqueConstraint(
            "student_enrollment_id", "subject_id", "exam_id",
            name="uq_enrollment_subject_exam"
        ),
    )

    # --- Relationships ---
    enrollment: Mapped["StudentEnrollment"] = relationship(
        "StudentEnrollment", back_populates="results"
    )
    subject: Mapped["Subject"] = relationship("Subject", back_populates="results")
    exam: Mapped["Exam"] = relationship("Exam", back_populates="results")

    def __repr__(self) -> str:
        return (
            f"<StudentResult(id={self.id}, enrollment={self.student_enrollment_id}, "
            f"subject={self.subject_id}, exam={self.exam_id}, "
            f"marks={self.marks_obtained}/{self.max_marks}, grade='{self.grade}')>"
        )
