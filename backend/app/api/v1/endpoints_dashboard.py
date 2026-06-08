"""
School Result Analysis System - Dashboard Endpoints

Aggregated APIs powering the student dashboard.
These endpoints use eager loading to avoid N+1 queries and
return a complete payload in a single response.

Authorization: Admin, Teacher, Principal (read-only for all).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.student import Student, StudentEnrollment
from app.models.academic import AcademicYear, ClassLevel, Exam, Subject
from app.models.result import StudentResult
from app.models.report import HistoricalReport
from app.schemas.dashboard_schema import (
    DashboardPayload,
    DashboardStudentInfo,
    DashboardEnrollment,
    ExamResult,
    SubjectResult,
    DashboardHistoricalReport,
)

router = APIRouter()


def _build_dashboard_payload(
    db: Session,
    student: Student,
    enrollment: StudentEnrollment,
) -> DashboardPayload:
    """Helper to assemble the master dashboard payload using eager loading."""
    
    # 1. Identity & Context
    student_info = DashboardStudentInfo(
        admission_number=student.admission_number,
        student_name=student.student_name,
    )
    
    enrollment_info = DashboardEnrollment(
        academic_year=enrollment.academic_year.year_label,
        class_name=enrollment.class_level.class_name,
        section=enrollment.section,
        roll_number=enrollment.roll_number,
    )

    # 2. Results (Eager load exam and subject)
    results_query = (
        db.query(StudentResult)
        .options(
            joinedload(StudentResult.exam),
            joinedload(StudentResult.subject),
        )
        .filter(StudentResult.student_enrollment_id == enrollment.id)
        .order_by(StudentResult.exam_id, StudentResult.subject_id)
        .all()
    )

    # Group by Exam
    exam_map = {}
    for r in results_query:
        if r.exam.id not in exam_map:
            exam_map[r.exam.id] = {
                "exam_id": r.exam.id,
                "exam_name": r.exam.exam_name,
                "subjects": []
            }
        
        percentage = None
        if r.max_marks and r.marks_obtained is not None and r.max_marks > 0:
            percentage = round((r.marks_obtained / r.max_marks) * 100, 2)
            
        exam_map[r.exam.id]["subjects"].append(
            SubjectResult(
                subject_id=r.subject.id,
                subject_name=r.subject.subject_name,
                max_marks=r.max_marks,
                marks_obtained=r.marks_obtained,
                percentage=percentage,
                grade=r.grade,
            )
        )

    grouped_results = [
        ExamResult(**exam_data) for exam_data in exam_map.values()
    ]
    # Sort exams by some order if available, else by ID
    # grouped_results.sort(key=lambda x: x.exam_id)

    # 3. Historical Reports
    reports_query = (
        db.query(HistoricalReport)
        .options(joinedload(HistoricalReport.academic_year))
        .filter(HistoricalReport.admission_number == student.admission_number)
        .order_by(HistoricalReport.academic_year_id.desc())
        .limit(2)  # Previous year, two years back
        .all()
    )

    historical_reports = [
        DashboardHistoricalReport(
            report_id=rep.id,
            academic_year=rep.academic_year.year_label,
            filename=rep.original_filename,
            download_url=f"/api/v1/reports/{rep.admission_number}/{rep.academic_year_id}/download"
        )
        for rep in reports_query
    ]

    return DashboardPayload(
        student=student_info,
        enrollment=enrollment_info,
        results=grouped_results,
        historical_reports=historical_reports,
    )


@router.get("/student", response_model=DashboardPayload)
def get_dashboard_by_roll_number(
    class_level_id: int = Query(...),
    section: str = Query(...),
    roll_number: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Search for a student using Class, Section, and Roll Number.
    Returns the complete dashboard payload for the current academic year.
    """
    # Find current academic year
    current_year = db.query(AcademicYear).filter_by(is_current=True).first()
    if not current_year:
        raise HTTPException(status_code=400, detail="No active academic year set.")

    # Find Enrollment (eager load class and year)
    enrollment = (
        db.query(StudentEnrollment)
        .options(
            joinedload(StudentEnrollment.class_level),
            joinedload(StudentEnrollment.academic_year)
        )
        .filter_by(
            academic_year_id=current_year.id,
            class_level_id=class_level_id,
            section=section.upper(),
            roll_number=roll_number,
        )
        .first()
    )

    if not enrollment:
        raise HTTPException(status_code=404, detail="Student enrollment not found.")

    # Find Student
    student = db.query(Student).filter_by(admission_number=enrollment.admission_number).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    return _build_dashboard_payload(db, student, enrollment)


@router.get("/student/{admission_number}", response_model=DashboardPayload)
def get_dashboard_by_admission_number(
    admission_number: str,
    academic_year_id: int | None = Query(None, description="Defaults to current year"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the complete dashboard payload by Admission Number.
    Defaults to the current academic year if not specified.
    """
    # Find Student
    student = db.query(Student).filter_by(admission_number=admission_number).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    # Determine Academic Year
    if not academic_year_id:
        current_year = db.query(AcademicYear).filter_by(is_current=True).first()
        if not current_year:
            raise HTTPException(status_code=400, detail="No active academic year set.")
        academic_year_id = current_year.id

    # Find Enrollment
    enrollment = (
        db.query(StudentEnrollment)
        .options(
            joinedload(StudentEnrollment.class_level),
            joinedload(StudentEnrollment.academic_year)
        )
        .filter_by(
            admission_number=admission_number,
            academic_year_id=academic_year_id,
        )
        .first()
    )

    if not enrollment:
        raise HTTPException(
            status_code=404, 
            detail=f"Student '{admission_number}' is not enrolled in the specified academic year."
        )

    return _build_dashboard_payload(db, student, enrollment)
