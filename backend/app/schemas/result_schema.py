"""
SPARSH - Result & Import Schemas

Pydantic DTOs for the Excel import workflow:
- Worksheet detection
- Smart analysis with confidence levels
- Import commit
- Batch tracking
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ============================================
# Worksheet Detection
# ============================================

class WorksheetListResponse(BaseModel):
    """List of worksheet names found in an uploaded workbook."""
    sheets: list[str]


# ============================================
# Smart Analysis Schemas
# ============================================

class DetectedSubjectSchema(BaseModel):
    """A subject column detected during smart analysis."""
    excel_column: str
    subject_id: int
    subject_name: str
    confidence: str  # "high" or "medium"


class SmartAnalysisResponse(BaseModel):
    """Full result of the smart workbook analysis."""
    headers_clean: list[str]
    total_rows: int
    detected_header_row: int
    detected_roll_column: str | None = None
    detected_name_column: str | None = None
    detected_admission_column: str | None = None
    detected_subjects: list[DetectedSubjectSchema]
    sample_rows: list[dict]
    issues: list[str]
    workbook_signature: str | None = None
    matched_template_name: str | None = None  # If a saved template matches
    detected_max_marks: dict[str, float] = {}


# ============================================
# Preview Schemas (Legacy compat)
# ============================================

class ImportPreviewRequest(BaseModel):
    """Metadata sent alongside the uploaded Excel file for preview."""
    academic_year_id: int
    class_level_id: int
    section: str
    exam_id: int


class PreviewRowData(BaseModel):
    """A single row from the parsed Excel, shown in the preview."""
    row_number: int
    data: dict[str, str | float | int | None]


class ImportPreviewResponse(BaseModel):
    """Returned after parsing the Excel file. No DB changes."""
    filename: str
    total_rows: int
    headers: list[str]
    sample_rows: list[PreviewRowData]
    detected_admission_column: str | None = None
    detected_max_marks: dict[str, float] = {}
    issues: list[str]


# ============================================
# Column Mapping Schemas
# ============================================

class ColumnMapping(BaseModel):
    """Maps an Excel column header to a database Subject."""
    excel_column: str
    subject_id: int


# ============================================
# Student Resolution Schemas
# ============================================

class UnresolvedRow(BaseModel):
    """A row where the student could not be auto-matched."""
    row_number: int
    row_data: dict[str, str | float | int | None]
    suggested_students: list[dict] = []


class StudentMapping(BaseModel):
    """User-confirmed mapping of an Excel row to a specific student."""
    row_number: int
    admission_number: str


# ============================================
# Import Commit Schemas
# ============================================

class ImportCommitRequest(BaseModel):
    """Full payload for committing an import after preview and mapping."""
    academic_year_id: int
    class_level_id: int
    section: str
    exam_id: int
    admission_number_column: str | None = None
    name_column: str | None = None
    roll_number_column: str | None = None
    dry_run: bool = False
    column_mappings: list[ColumnMapping]
    student_mappings: list[StudentMapping] = []


class ImportValidationRow(BaseModel):
    """Validation result for a single row during import."""
    row_number: int
    admission_number: str | None = None
    student_name: str | None = None
    status: str  # "ok", "skipped", "error"
    message: str = ""
    results_imported: int = 0


class ImportCommitResponse(BaseModel):
    """Summary returned after a successful import commit."""
    batch_id: int | None = None
    filename: str
    status: str
    total_rows: int
    imported_rows: int
    skipped_rows: int
    students_created: int = 0
    existing_students_matched: int = 0
    enrollments_created: int = 0
    row_details: list[ImportValidationRow]


# ============================================
# Import Batch Schemas
# ============================================

class ImportBatchResponse(BaseModel):
    """Import batch record returned by API."""
    id: int
    filename: str
    academic_year_id: int
    class_level_id: int
    exam_id: int
    section: str
    uploaded_by: int
    uploaded_at: datetime
    status: str
    total_rows: int
    imported_rows: int
    skipped_rows: int
    students_created: int
    existing_students_matched: int
    enrollments_created: int

    model_config = ConfigDict(from_attributes=True)
