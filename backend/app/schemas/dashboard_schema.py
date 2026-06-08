"""
School Result Analysis System - Dashboard Schemas

Aggregated DTOs for the student dashboard. Designed to minimize
frontend API calls by providing all necessary data in a single payload.
"""

from pydantic import BaseModel, ConfigDict


# ============================================
# Result Representation
# ============================================

class SubjectResult(BaseModel):
    """Result for a single subject."""
    subject_id: int
    subject_name: str
    max_marks: float | None = None
    marks_obtained: float | None = None
    percentage: float | None = None
    grade: str | None = None


class ExamResult(BaseModel):
    """Results grouped by exam."""
    exam_id: int
    exam_name: str
    subjects: list[SubjectResult]


# ============================================
# Dashboard Aggregation
# ============================================

class DashboardHistoricalReport(BaseModel):
    """Metadata for a historical report."""
    report_id: int
    academic_year: str
    filename: str
    download_url: str


class DashboardStudentInfo(BaseModel):
    """Basic student identity."""
    admission_number: str
    student_name: str


class DashboardEnrollment(BaseModel):
    """Current or requested enrollment context."""
    academic_year: str
    class_name: str
    section: str
    roll_number: int


class DashboardPayload(BaseModel):
    """
    The master dashboard payload.
    Contains identity, context, current year results, and history.
    """
    student: DashboardStudentInfo
    enrollment: DashboardEnrollment
    results: list[ExamResult]  # Grouped by exam
    historical_reports: list[DashboardHistoricalReport]

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Result Summary
# ============================================

class ResultSummary(BaseModel):
    """High-level metrics for a student's results."""
    admission_number: str
    total_subjects_evaluated: int
    exams_available: int
    marks_entered: int
    grades_entered: int
