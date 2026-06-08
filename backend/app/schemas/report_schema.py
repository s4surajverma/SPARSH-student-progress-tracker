"""
School Result Analysis System - Historical Report Schemas

Pydantic DTOs for report upload, ZIP processing, and retrieval.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ============================================
# Report Response
# ============================================

class ReportResponse(BaseModel):
    """Historical report metadata returned by API."""
    id: int
    admission_number: str
    academic_year_id: int
    storage_provider: str
    storage_key: str
    original_filename: str
    uploaded_by: int
    uploaded_at: datetime

    # Resolved display names
    student_name: str | None = None
    year_label: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ============================================
# Single Upload
# ============================================

class SingleUploadResponse(BaseModel):
    """Response after uploading a single PDF."""
    report_id: int
    admission_number: str
    academic_year: str
    original_filename: str
    message: str


# ============================================
# ZIP Upload Schemas
# ============================================

class ZipFileEntry(BaseModel):
    """A single file detected inside a ZIP archive."""
    filename: str
    admission_number: str | None = None
    academic_year: str | None = None
    status: str  # "matched", "student_not_found", "year_not_found", "invalid_format", "duplicate"
    message: str = ""


class ZipPreviewResponse(BaseModel):
    """Preview returned after scanning a ZIP file (no DB changes)."""
    total_files: int
    matched: int
    errors: int
    entries: list[ZipFileEntry]


class ZipUploadResult(BaseModel):
    """Result for a single file within a ZIP import."""
    filename: str
    admission_number: str | None = None
    academic_year: str | None = None
    status: str  # "uploaded", "skipped", "error"
    message: str = ""


class ZipImportResponse(BaseModel):
    """Summary returned after committing a ZIP import."""
    total_files: int
    uploaded: int
    skipped: int
    errors: int
    results: list[ZipUploadResult]
