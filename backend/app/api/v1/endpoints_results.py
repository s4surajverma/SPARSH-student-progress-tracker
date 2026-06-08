"""
SPARSH - Result Import Endpoints

APIs for the Smart Excel import workflow:
- POST /worksheets  — Detect worksheets in uploaded workbook
- POST /analyze     — Smart analysis of a selected worksheet
- POST /preview     — Legacy preview (kept for backward compat)
- POST /import      — Validate, import, and commit results
- GET  /batches     — List import history

Authorization:
- Admin / Teacher: Can analyze and import
- Principal: Read-only (batch history)
"""

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Query
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db,
    get_current_active_user,
    require_role,
)
from app.models.user import User
from app.models.academic import AcademicYear, ClassLevel, Subject, Exam
from app.models.import_batch import ImportBatch
from app.models.template import ImportTemplate
from app.services.excel_service import (
    detect_worksheets,
    smart_analyze,
    parse_excel_for_import,
    parse_excel_file,
    validate_and_import,
)
from app.schemas.result_schema import (
    WorksheetListResponse,
    SmartAnalysisResponse,
    DetectedSubjectSchema,
    PreviewRowData,
    ImportPreviewResponse,
    ImportValidationRow,
    ImportCommitResponse,
    ImportBatchResponse,
)

router = APIRouter()

# Max rows to include in the preview sample
PREVIEW_SAMPLE_SIZE = 10

# Allowed file extensions
ALLOWED_EXTENSIONS = {".xlsx"}


def _validate_file(file: UploadFile) -> None:
    """Validate that the uploaded file is a .xlsx Excel file."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided.",
        )
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Only .xlsx files are accepted.",
        )


def _get_current_academic_year(db: Session) -> AcademicYear:
    """Get the current active academic year. Raises 400 if none is set."""
    year = db.query(AcademicYear).filter_by(is_current=True).first()
    if not year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active academic year is configured. Please ask the administrator to set one.",
        )
    return year


# ============================================
# POST — Detect Worksheets
# ============================================

@router.post("/worksheets", response_model=WorksheetListResponse)
async def get_worksheets(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    """
    Upload an Excel file and return the list of worksheet names.
    """
    _validate_file(file)
    file_bytes = await file.read()
    sheets = detect_worksheets(file_bytes)

    if not sheets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read the uploaded file. Please ensure it is a valid .xlsx file.",
        )

    return WorksheetListResponse(sheets=sheets)


# ============================================
# POST — Smart Analysis
# ============================================

@router.post("/analyze", response_model=SmartAnalysisResponse)
async def analyze_worksheet(
    file: UploadFile = File(...),
    sheet_name: str = Form(...),
    header_row: int = Form(None),
    class_level_id: int = Form(...),
    section: str = Form(...),
    exam_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    """
    Perform smart analysis on a selected worksheet.
    Auto-detects header row, identity columns, and subject columns.
    Academic year is automatically set to the current active year.
    """
    _validate_file(file)

    # Validate references
    current_year = _get_current_academic_year(db)
    if not db.query(ClassLevel).filter_by(id=class_level_id).first():
        raise HTTPException(status_code=404, detail="Class level not found.")
    if not db.query(Exam).filter_by(id=exam_id).first():
        raise HTTPException(status_code=404, detail="Exam not found.")

    # Fetch all subjects from DB for matching
    db_subjects = db.query(Subject).all()

    file_bytes = await file.read()
    result = smart_analyze(
        file_bytes=file_bytes,
        sheet_name=sheet_name,
        db_subjects=db_subjects,
        header_row=header_row,
    )

    # Check for matching auto-template signature
    matched_template_name = None
    if result.workbook_signature:
        templates = db.query(ImportTemplate).all()
        for t in templates:
            if isinstance(t.mapping_json, list) and len(t.mapping_json) > 0:
                first = t.mapping_json[0]
                if isinstance(first, dict) and first.get("workbook_signature") == result.workbook_signature:
                    matched_template_name = t.template_name
                    break

    return SmartAnalysisResponse(
        headers_clean=result.headers_clean,
        total_rows=result.total_rows,
        detected_header_row=result.detected_header_row,
        detected_roll_column=result.detected_roll_column,
        detected_name_column=result.detected_name_column,
        detected_admission_column=result.detected_admission_column,
        detected_subjects=[
            DetectedSubjectSchema(
                excel_column=s.excel_column,
                subject_id=s.subject_id,
                subject_name=s.subject_name,
                confidence=s.confidence,
            )
            for s in result.detected_subjects
        ],
        sample_rows=result.sample_rows,
        issues=result.issues,
        workbook_signature=result.workbook_signature,
        matched_template_name=matched_template_name,
        detected_max_marks=result.detected_max_marks,
    )


# ============================================
# POST — Legacy Preview (kept for compat)
# ============================================

@router.post("/preview", response_model=ImportPreviewResponse)
async def preview_import(
    file: UploadFile = File(...),
    academic_year_id: int = Form(...),
    class_level_id: int = Form(...),
    section: str = Form(...),
    exam_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    """
    Legacy preview endpoint. Maintained for backward compatibility.
    New imports should use /worksheets → /analyze → /import.
    """
    _validate_file(file)

    if not db.query(AcademicYear).filter_by(id=academic_year_id).first():
        raise HTTPException(status_code=404, detail="Academic year not found.")
    if not db.query(ClassLevel).filter_by(id=class_level_id).first():
        raise HTTPException(status_code=404, detail="Class level not found.")
    if not db.query(Exam).filter_by(id=exam_id).first():
        raise HTTPException(status_code=404, detail="Exam not found.")

    file_bytes = await file.read()
    parsed = parse_excel_file(file_bytes, file.filename)

    if parsed.total_rows == 0 and parsed.issues:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=parsed.issues[0],
        )

    sample_rows = [
        PreviewRowData(row_number=idx + 2, data=row)
        for idx, row in enumerate(parsed.rows[:PREVIEW_SAMPLE_SIZE])
    ]

    return ImportPreviewResponse(
        filename=file.filename,
        total_rows=parsed.total_rows,
        headers=parsed.headers,
        sample_rows=sample_rows,
        detected_admission_column=parsed.detected_admission_column,
        detected_max_marks=parsed.subject_max_marks,
        issues=parsed.issues,
    )


# ============================================
# POST — Import Results
# ============================================

@router.post("/import", response_model=ImportCommitResponse)
async def import_results(
    file: UploadFile = File(...),
    import_config: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    """
    Import student results from an Excel file.

    The `import_config` form field must be a JSON string containing:
    - academic_year_id, class_level_id, section, exam_id
    - column_mappings: [{excel_column, subject_id}, ...]
    - Optional: sheet_name, header_row, admission_number_column, student_mappings
    - Optional: workbook_signature (for auto-template save)
    """
    _validate_file(file)

    try:
        config = json.loads(import_config)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="import_config must be a valid JSON string.",
        )

    academic_year_id = config.get("academic_year_id")
    class_level_id = config.get("class_level_id")
    section = config.get("section", "")
    exam_id = config.get("exam_id")
    admission_number_column = config.get("admission_number_column")
    name_column = config.get("name_column")
    roll_number_column = config.get("roll_number_column")
    dry_run = config.get("dry_run", False)
    column_mappings = config.get("column_mappings", [])
    student_mappings = config.get("student_mappings", [])
    sheet_name = config.get("sheet_name")
    header_row = config.get("header_row", 0)
    workbook_signature = config.get("workbook_signature")

    if not all([academic_year_id, class_level_id, section, exam_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="import_config must include academic_year_id, class_level_id, section, and exam_id.",
        )

    if not column_mappings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one column_mapping is required.",
        )

    # Validate references
    if not db.query(AcademicYear).filter_by(id=academic_year_id).first():
        raise HTTPException(status_code=404, detail="Academic year not found.")
    if not db.query(ClassLevel).filter_by(id=class_level_id).first():
        raise HTTPException(status_code=404, detail="Class level not found.")
    if not db.query(Exam).filter_by(id=exam_id).first():
        raise HTTPException(status_code=404, detail="Exam not found.")

    # Parse the Excel file using confirmed sheet/header
    file_bytes = await file.read()

    if sheet_name:
        parsed = parse_excel_for_import(file_bytes, sheet_name, header_row)
    else:
        parsed = parse_excel_file(file_bytes, file.filename)

    if parsed.total_rows == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Excel file contains no data rows.",
        )

    # Run validation and import
    row_results = validate_and_import(
        db=db,
        parsed=parsed,
        academic_year_id=academic_year_id,
        class_level_id=class_level_id,
        section=section,
        exam_id=exam_id,
        column_mappings=column_mappings,
        admission_number_column=admission_number_column,
        name_column=name_column,
        roll_number_column=roll_number_column,
        student_mappings=student_mappings,
    )

    # Count outcomes
    imported_count = sum(1 for r in row_results if r.status == "ok")
    skipped_count = sum(1 for r in row_results if r.status == "skipped")
    error_count = sum(1 for r in row_results if r.status == "error")

    students_created_count = sum(1 for r in row_results if getattr(r, 'student_created', False))
    students_matched_count = sum(1 for r in row_results if getattr(r, 'student_matched', False))
    enrollments_created_count = sum(1 for r in row_results if getattr(r, 'enrollment_created', False))

    batch_status = "completed" if error_count == 0 else "completed_with_errors"
    if imported_count == 0:
        batch_status = "failed"

    if dry_run:
        # Rollback all DB changes to simulate a dry run
        db.rollback()
        batch_id = None
    else:
        # Create audit record
        batch = ImportBatch(
            filename=file.filename,
            academic_year_id=academic_year_id,
            class_level_id=class_level_id,
            exam_id=exam_id,
            section=section.upper(),
            uploaded_by=current_user.id,
            status=batch_status,
            total_rows=parsed.total_rows,
            imported_rows=imported_count,
            skipped_rows=skipped_count + error_count,
            students_created=students_created_count,
            existing_students_matched=students_matched_count,
            enrollments_created=enrollments_created_count,
        )
        db.add(batch)

        # Auto-save template if import succeeded and signature provided
        if imported_count > 0 and workbook_signature:
            auto_name = f"Auto - {file.filename}"
            existing_auto = db.query(ImportTemplate).filter(
                ImportTemplate.template_name == auto_name
            ).first()

            template_data = [
                {"workbook_signature": workbook_signature},
                *column_mappings,
            ]

            if existing_auto:
                existing_auto.mapping_json = template_data
            else:
                auto_template = ImportTemplate(
                    template_name=auto_name,
                    mapping_json=template_data,
                    created_by=current_user.id,
                )
                db.add(auto_template)

        # Commit everything
        db.commit()
        db.refresh(batch)
        batch_id = batch.id

    return ImportCommitResponse(
        batch_id=batch_id,
        filename=file.filename,
        status=batch_status,
        total_rows=parsed.total_rows,
        imported_rows=imported_count,
        skipped_rows=skipped_count + error_count,
        students_created=students_created_count,
        existing_students_matched=students_matched_count,
        enrollments_created=enrollments_created_count,
        row_details=[
            ImportValidationRow(
                row_number=r.row_number,
                admission_number=r.admission_number,
                student_name=r.student_name,
                status=r.status,
                message=r.message,
                results_imported=r.results_imported,
            )
            for r in row_results
        ],
    )


# ============================================
# GET — Import Batch History
# ============================================

@router.get("/batches", response_model=list[ImportBatchResponse])
def list_import_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all import batches, most recent first."""
    return (
        db.query(ImportBatch)
        .order_by(ImportBatch.uploaded_at.desc())
        .limit(50)
        .all()
    )


@router.get("/batches/{batch_id}", response_model=ImportBatchResponse)
def get_import_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get details of a specific import batch."""
    batch = db.query(ImportBatch).filter_by(id=batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found.")
    return batch


# ============================================
# RESULT RETRIEVAL
# ============================================

from app.schemas.dashboard_schema import ResultSummary, ExamResult, SubjectResult
from app.models.student import Student, StudentEnrollment
from app.models.result import StudentResult
from sqlalchemy.orm import joinedload
from sqlalchemy import func

@router.get("/student/{admission_number}/summary", response_model=ResultSummary)
def get_student_result_summary(
    admission_number: str,
    academic_year_id: int | None = Query(None, description="Defaults to current year"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get high-level result metrics for a student."""
    if not academic_year_id:
        current_year = db.query(AcademicYear).filter_by(is_current=True).first()
        if not current_year:
            raise HTTPException(status_code=400, detail="No active academic year set.")
        academic_year_id = current_year.id

    enrollment = db.query(StudentEnrollment).filter_by(
        admission_number=admission_number,
        academic_year_id=academic_year_id
    ).first()

    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found.")

    results = db.query(StudentResult).filter_by(student_enrollment_id=enrollment.id).all()
    
    exams_available = len(set(r.exam_id for r in results))
    total_subjects = len(set(r.subject_id for r in results))
    marks_entered = sum(1 for r in results if r.marks_obtained is not None)
    grades_entered = sum(1 for r in results if r.grade is not None)

    return ResultSummary(
        admission_number=admission_number,
        total_subjects_evaluated=total_subjects,
        exams_available=exams_available,
        marks_entered=marks_entered,
        grades_entered=grades_entered
    )


@router.get("/student/{admission_number}", response_model=list[ExamResult])
def get_results_by_student(
    admission_number: str,
    academic_year_id: int | None = Query(None, description="Defaults to current year"),
    exam_id: int | None = Query(None),
    subject_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve raw results for a student, optionally filtered."""
    if not academic_year_id:
        current_year = db.query(AcademicYear).filter_by(is_current=True).first()
        if not current_year:
            raise HTTPException(status_code=400, detail="No active academic year set.")
        academic_year_id = current_year.id

    enrollment = db.query(StudentEnrollment).filter_by(
        admission_number=admission_number,
        academic_year_id=academic_year_id
    ).first()

    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found.")

    return _fetch_and_group_results(db, enrollment.id, exam_id, subject_id)


@router.get("/enrollment/{enrollment_id}", response_model=list[ExamResult])
def get_results_by_enrollment(
    enrollment_id: int,
    exam_id: int | None = Query(None),
    subject_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve raw results for a specific enrollment, optionally filtered."""
    enrollment = db.query(StudentEnrollment).filter_by(id=enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found.")

    return _fetch_and_group_results(db, enrollment.id, exam_id, subject_id)


def _fetch_and_group_results(db: Session, enrollment_id: int, exam_id: int | None, subject_id: int | None) -> list[ExamResult]:
    """Helper to fetch and group results by exam."""
    query = (
        db.query(StudentResult)
        .options(
            joinedload(StudentResult.exam),
            joinedload(StudentResult.subject),
        )
        .filter(StudentResult.student_enrollment_id == enrollment_id)
    )

    if exam_id:
        query = query.filter(StudentResult.exam_id == exam_id)
    if subject_id:
        query = query.filter(StudentResult.subject_id == subject_id)

    results_query = query.order_by(StudentResult.exam_id, StudentResult.subject_id).all()

    exam_map = {}
    for r in results_query:
        if r.exam.id not in exam_map:
            exam_map[r.exam.id] = {
                "exam_id": r.exam.id,
                "exam_name": r.exam.exam_name,
                "subjects": []
            }
        
        exam_map[r.exam.id]["subjects"].append(
            SubjectResult(
                subject_id=r.subject.id,
                subject_name=r.subject.subject_name,
                marks_obtained=r.marks_obtained,
                grade=r.grade,
            )
        )

    return [ExamResult(**exam_data) for exam_data in exam_map.values()]
