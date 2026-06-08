"""
SPARSH - Excel Import Service (Smart Analysis Engine)

Handles intelligent parsing of KVS-style Excel files for result ingestion.

Key capabilities:
- Worksheet detection
- Header row auto-detection (handles merged headers, school name rows, etc.)
- Alias-based subject matching (SST → Social Science, Eng → English, etc.)
- Fuzzy matching fallback (difflib.SequenceMatcher)
- Identity column detection (Roll No, Student Name, Admission Number)
- Unnamed column filtering
- Workbook signature generation for auto-template memory

This service is stateless — each call receives raw file bytes
and returns structured data without side effects (except for commit).
"""

import io
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import pandas as pd
import openpyxl
from sqlalchemy.orm import Session

from app.models.student import Student, StudentEnrollment
from app.models.academic import AcademicYear, ClassLevel, Subject, Exam
from app.models.result import StudentResult

logger = logging.getLogger(__name__)


# ============================================
# Alias Dictionaries
# ============================================

SUBJECT_ALIASES: dict[str, str] = {
    # English
    "eng": "English", "eng.": "English", "english": "English", "engl": "English",
    "engg": "English",
    # Hindi
    "hin": "Hindi", "hin.": "Hindi", "hindi": "Hindi",
    # Mathematics
    "math": "Mathematics", "maths": "Mathematics", "mathematics": "Mathematics",
    "mat": "Mathematics", "mat.": "Mathematics",
    # Science
    "sci": "Science", "sci.": "Science", "science": "Science",
    "gen sci": "Science", "gen. sci.": "Science", "general science": "Science",
    # Social Science / Social Studies
    "sst": "Social Science", "s.st": "Social Science", "s.st.": "Social Science",
    "s.sc": "Social Science", "s.sc.": "Social Science",
    "soc sci": "Social Science", "soc. sci": "Social Science",
    "soc. sci.": "Social Science", "social science": "Social Science",
    "social studies": "Social Science",
    # Computer Science
    "comp": "Computer Science", "comp.": "Computer Science",
    "comp sci": "Computer Science", "comp. sci": "Computer Science",
    "comp. sci.": "Computer Science", "computer": "Computer Science",
    "computer science": "Computer Science", "cs": "Computer Science",
    # Sanskrit
    "sans": "Sanskrit", "sans.": "Sanskrit", "sanskrit": "Sanskrit",
    "sansk": "Sanskrit",
    # Artificial Intelligence
    "ai": "Artificial Intelligence", "a.i.": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    # Physical Education
    "pe": "Physical Education", "p.e.": "Physical Education",
    "phy edu": "Physical Education", "phy. edu.": "Physical Education",
    "physical education": "Physical Education", "health & pe": "Physical Education",
    # Art / Art Education
    "art": "Art Education", "art edu": "Art Education",
    "art education": "Art Education",
    # Music
    "music": "Music",
    # Work Education / Work Experience
    "we": "Work Education", "w.e.": "Work Education",
    "work edu": "Work Education", "work education": "Work Education",
    "work experience": "Work Education", "supw": "Work Education",
    # Physics
    "phy": "Physics", "phy.": "Physics", "physics": "Physics",
    # Chemistry
    "chem": "Chemistry", "chem.": "Chemistry", "chemistry": "Chemistry",
    # Biology
    "bio": "Biology", "bio.": "Biology", "biology": "Biology",
    # Accountancy
    "acc": "Accountancy", "acct": "Accountancy", "accountancy": "Accountancy",
    "accounts": "Accountancy",
    # Business Studies
    "bs": "Business Studies", "b.st": "Business Studies",
    "business studies": "Business Studies", "bus. studies": "Business Studies",
    # Economics
    "eco": "Economics", "eco.": "Economics", "economics": "Economics",
    # Political Science
    "pol sci": "Political Science", "pol. sci.": "Political Science",
    "political science": "Political Science",
    # History
    "hist": "History", "history": "History",
    # Geography
    "geo": "Geography", "geo.": "Geography", "geography": "Geography",
    # Information Practices
    "ip": "Information Practices", "i.p.": "Information Practices",
    "info practices": "Information Practices",
    "information practices": "Information Practices",
    # Home Science
    "home sci": "Home Science", "home science": "Home Science",
}

ROLL_HINTS = [
    "roll", "roll no", "roll no.", "roll. no", "roll. no.", "roll number", "rollno", "roll_no",
    "r.no", "r no", "rno", "sl no", "sl no.", "sl.no", "sl.no.",
    "s.no", "s.no.", "s no", "sno", "sr no", "sr no.", "sr.no",
    "serial", "serial no", "serial no.", "serial number",
]

NAME_HINTS = [
    "name", "student name", "student's name", "pupil name",
    "name of student", "name of the student", "student",
    "students name", "stu name", "stu. name",
]

ADMISSION_HINTS = [
    "admission number", "admission no", "admission no.", "admission. no", "admission. no.",
    "admission_number", "adm no", "adm no.", "adm. no", "adm. no.", "adm_no",
    "admno", "adm number", "admission", "adm",
    "admission #", "adm #", "admit no",
]

# Columns to always ignore (non-data markers)
IGNORE_HINTS = [
    "total", "total marks", "percentage", "%", "percent", "result",
    "grade", "overall", "aggregate", "rank", "position", "division",
    "pass/fail", "pass / fail", "remarks", "remark", "attendance",
    "max marks", "max", "maximum", "out of",
]


# ============================================
# Data Classes
# ============================================

@dataclass
class DetectedSubject:
    """A subject column detected during smart analysis."""
    excel_column: str
    subject_id: int
    subject_name: str
    confidence: str  # "high" (alias/exact match) or "medium" (fuzzy match)


@dataclass
class SmartAnalysisResult:
    """Complete result of smart workbook analysis."""
    headers_clean: list[str]
    total_rows: int
    detected_header_row: int
    detected_roll_column: str | None = None
    detected_name_column: str | None = None
    detected_admission_column: str | None = None
    detected_subjects: list[DetectedSubject] = field(default_factory=list)
    sample_rows: list[dict] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    workbook_signature: str | None = None
    detected_max_marks: dict[str, float] = field(default_factory=dict)


@dataclass
class ParsedExcel:
    """Result of parsing an Excel file (used by import step)."""
    headers: list[str]
    rows: list[dict]
    total_rows: int
    detected_admission_column: str | None = None
    issues: list[str] = field(default_factory=list)
    subject_max_marks: dict[str, float] = field(default_factory=dict)


@dataclass
class RowImportResult:
    """Outcome of importing a single row."""
    row_number: int
    admission_number: str | None = None
    student_name: str | None = None
    status: str = "ok"  # ok, skipped, error
    message: str = ""
    results_imported: int = 0
    student_created: bool = False
    student_matched: bool = False
    enrollment_created: bool = False


# ============================================
# Worksheet Detection
# ============================================

def detect_worksheets(file_bytes: bytes) -> list[str]:
    """Return all worksheet names from an Excel file."""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        names = wb.sheetnames
        wb.close()
        return names
    except Exception as e:
        logger.error(f"Failed to read worksheets: {e}")
        return []


# ============================================
# Header Row Detection
# ============================================

def detect_header_row(file_bytes: bytes, sheet_name: str, max_scan: int = 15) -> int:
    """
    Detect the most likely header row by scanning the first `max_scan` rows.

    Strategy: The header row is the row with the most non-numeric,
    non-empty, unique string cells. Rows containing a single cell
    (like "School Name") or entirely numeric rows score low.
    """
    try:
        df_raw = pd.read_excel(
            io.BytesIO(file_bytes), sheet_name=sheet_name,
            header=None, nrows=max_scan, engine="openpyxl"
        )
    except Exception:
        return 0

    best_row = 0
    best_score = 0

    for idx in range(len(df_raw)):
        row_vals = df_raw.iloc[idx]
        non_null = [v for v in row_vals if pd.notna(v)]

        if len(non_null) < 2:
            continue  # Skip rows with 0-1 values (school name, blank rows)

        string_vals = []
        for v in non_null:
            s = str(v).strip()
            if s and not s.replace('.', '', 1).replace('-', '', 1).isdigit():
                string_vals.append(s.lower())

        # Penalize rows where all values are the same (merged header label)
        unique_count = len(set(string_vals))

        # Score: unique string count, bonus for subject-like words
        score = unique_count
        for sv in string_vals:
            normalized = sv.lower().strip().rstrip('.')
            if normalized in SUBJECT_ALIASES or normalized in ROLL_HINTS or normalized in NAME_HINTS:
                score += 2  # Bonus for recognized vocabulary

        if score > best_score:
            best_score = score
            best_row = idx

    return best_row

def _extract_max_marks(df: pd.DataFrame, df_columns: list[str]) -> dict[str, float]:
    """
    Extracts max marks from metadata rows before they are filtered out.
    Returns a dict mapping the cleaned subject header to its max marks.
    """
    import re
    MAX_MARK_HINTS = ["max mark", "max marks", "max", "maximum marks", "mm", "out of"]
    subject_max_marks = {}
    
    # Scan the first 10 rows for metadata
    for idx in range(min(10, len(df))):
        row = df.iloc[idx]
        
        row_str_lower = [str(v).strip().lower() for v in row.values if pd.notna(v)]
        has_hint = False
        for cell in row_str_lower:
            for hint in MAX_MARK_HINTS:
                if hint == cell or cell.startswith(hint + " ") or cell.startswith(hint + ":"):
                    has_hint = True
                    break
            if has_hint: break
            
        if not has_hint:
            continue
            
        # Found a max mark metadata row. Match numbers to subjects.
        last_seen_subject = None
        for col_idx, col_name in enumerate(df_columns):
            col_name_str = str(col_name).strip()
            
            # If this is a named ignored column (like TOTAL), break association
            if _is_ignored_column(col_name_str) and not _is_unnamed(col_name_str):
                last_seen_subject = None
                continue
                
            # If it's a valid subject header, update association
            if not _is_unnamed(col_name_str):
                last_seen_subject = col_name_str
            
            if not last_seen_subject:
                continue
                
            val = row.iloc[col_idx]
            if pd.notna(val):
                val_str = str(val).strip().lower()
                try:
                    num = float(val_str)
                    if num > 0:
                        subject_max_marks[last_seen_subject] = num
                except ValueError:
                    match = re.search(r'\b(\d+(?:\.\d+)?)\b', val_str)
                    if match:
                        num = float(match.group(1))
                        if num > 0:
                            subject_max_marks[last_seen_subject] = num
                            
    return subject_max_marks

def _filter_junk_rows(df: pd.DataFrame, detected_name: str, detected_roll: str, detected_admission: str) -> pd.DataFrame:
    """Filter out non-student metadata rows (e.g., 'Class Teacher', 'max mark')."""
    if df.empty:
        return df

    valid_mask = pd.Series(True, index=df.index)

    if detected_name and detected_name in df.columns:
        valid_mask &= df[detected_name].notna()
        names = df[detected_name].fillna('').astype(str).str.strip().str.lower()
        # Ensure it's not a known metadata pattern
        valid_mask &= (names != '') & (~names.str.contains(r'signature|teacher|max mark|marks|%|total', na=False))

    id_mask = pd.Series(False, index=df.index)
    has_id_col = False
    
    if detected_roll and detected_roll in df.columns:
        has_id_col = True
        id_mask |= df[detected_roll].notna() & (df[detected_roll].astype(str).str.strip().str.lower() != 'nan')
        
    if detected_admission and detected_admission in df.columns:
        has_id_col = True
        id_mask |= df[detected_admission].notna() & (df[detected_admission].astype(str).str.strip().str.lower() != 'nan')

    if has_id_col:
        valid_mask &= id_mask

    return df[valid_mask].copy()

# ============================================
# Column Matching Helpers
# ============================================

def _normalize(s: str) -> str:
    """Normalize a column header for comparison."""
    return re.sub(r'\s+', ' ', str(s).strip().lower().rstrip('.'))


def _is_unnamed(col: str) -> bool:
    """Check if a column name is an auto-generated pandas placeholder."""
    return bool(re.match(r'^unnamed:\s*\d+$', str(col).strip().lower()))


def _is_ignored_column(col: str) -> bool:
    """Check if a column should be completely excluded from processing and UI."""
    if _is_unnamed(col):
        return True
    normalized = _normalize(col)
    if normalized in [h.lower() for h in IGNORE_HINTS]:
        return True
    return False


def _match_identity_column(header: str, hints: list[str]) -> bool:
    """Check if a header matches any hint from a list."""
    normalized = _normalize(header)
    return normalized in [h.lower() for h in hints]


def _match_subject(header: str, db_subjects: list) -> DetectedSubject | None:
    """
    Try to match a header to a system subject.

    Priority:
    1. Alias dictionary → High confidence
    2. Exact DB name match → High confidence
    3. Fuzzy match (≥ 0.75) → Medium confidence
    """
    normalized = _normalize(header)

    # Skip identity and ignore columns
    all_identity = ROLL_HINTS + NAME_HINTS + ADMISSION_HINTS + IGNORE_HINTS
    if normalized in [h.lower() for h in all_identity]:
        return None

    # 1. Alias lookup
    if normalized in SUBJECT_ALIASES:
        canonical = SUBJECT_ALIASES[normalized]
        for sub in db_subjects:
            if sub.subject_name.lower() == canonical.lower():
                return DetectedSubject(
                    excel_column=header,
                    subject_id=sub.id,
                    subject_name=sub.subject_name,
                    confidence="high",
                )

    # 2. Exact DB name match
    for sub in db_subjects:
        if sub.subject_name.lower() == normalized:
            return DetectedSubject(
                excel_column=header,
                subject_id=sub.id,
                subject_name=sub.subject_name,
                confidence="high",
            )
        # Also check subject_code
        if sub.subject_code and sub.subject_code.lower() == normalized:
            return DetectedSubject(
                excel_column=header,
                subject_id=sub.id,
                subject_name=sub.subject_name,
                confidence="high",
            )

    # 3. Fuzzy matching against DB subject names
    best_match = None
    best_ratio = 0.0
    for sub in db_subjects:
        ratio = SequenceMatcher(None, normalized, sub.subject_name.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = sub

    if best_ratio >= 0.75 and best_match:
        return DetectedSubject(
            excel_column=header,
            subject_id=best_match.id,
            subject_name=best_match.subject_name,
            confidence="medium",
        )

    return None


# ============================================
# Workbook Signature Generation
# ============================================

def generate_workbook_signature(
    sheet_name: str,
    header_row: int,
    headers_clean: list[str],
) -> str:
    """
    Generate a stable hash signature for a workbook's structure.
    Used for auto-template memory to recognize returning formats.
    """
    payload = {
        "sheet_name": sheet_name,
        "header_row": header_row,
        "columns": [h.lower().strip() for h in sorted(headers_clean)],
    }
    payload_str = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(payload_str.encode()).hexdigest()[:16]


# ============================================
# Smart Analysis (Main Function)
# ============================================

def smart_analyze(
    file_bytes: bytes,
    sheet_name: str,
    db_subjects: list,
    header_row: int | None = None,
) -> SmartAnalysisResult:
    """
    Perform a full smart analysis of a worksheet.

    Args:
        file_bytes: Raw bytes of the .xlsx file.
        sheet_name: Name of the worksheet to analyze.
        db_subjects: List of Subject model instances from the database.
        header_row: Override for the header row (0-indexed). If None, auto-detected.

    Returns:
        SmartAnalysisResult with all detections and sample data.
    """
    issues = []

    # Auto-detect header row if not provided
    if header_row is None:
        header_row = detect_header_row(file_bytes, sheet_name)

    # Parse the sheet with the detected header
    try:
        df = pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name=sheet_name,
            header=header_row,
            engine="openpyxl",
        )
    except Exception as e:
        logger.error(f"Failed to parse sheet '{sheet_name}' with header row {header_row}: {e}")
        return SmartAnalysisResult(
            headers_clean=[], total_rows=0, detected_header_row=header_row,
            issues=[f"Failed to read the selected worksheet."],
        )

    if df.empty:
        return SmartAnalysisResult(
            headers_clean=[], total_rows=0, detected_header_row=header_row,
            issues=["The selected worksheet contains no data."],
        )

    # Clean headers: strip whitespace, filter out ignored columns
    raw_headers = [str(col).strip() for col in df.columns]
    headers_clean = [h for h in raw_headers if not _is_ignored_column(h)]

    # Detect identity columns
    detected_roll = None
    detected_name = None
    detected_admission = None

    for h in headers_clean:
        if not detected_roll and _match_identity_column(h, ROLL_HINTS):
            detected_roll = h
        elif not detected_name and _match_identity_column(h, NAME_HINTS):
            detected_name = h
        elif not detected_admission and _match_identity_column(h, ADMISSION_HINTS):
            detected_admission = h

    # Detect subjects
    detected_subjects = []
    for h in headers_clean:
        # Skip already-identified identity columns
        if h in [detected_roll, detected_name, detected_admission]:
            continue
        match = _match_subject(h, db_subjects)
        if match:
            detected_subjects.append(match)

    # Extract max marks from metadata rows
    raw_max_marks = _extract_max_marks(df, raw_headers)
    
    # Normalize keys to subject names
    normalized_max_marks = {}
    for excel_col, max_val in raw_max_marks.items():
        # Try to find if this column was matched to a known subject
        matched = next((s for s in detected_subjects if s.excel_column == excel_col), None)
        if matched:
            normalized_max_marks[matched.subject_name] = max_val
        else:
            normalized_max_marks[excel_col.title()] = max_val

    # Clean dataframe from junk metadata rows
    df_clean = _filter_junk_rows(df, detected_name, detected_roll, detected_admission)

    # Build sample rows (first 10, only with clean columns)
    sample_rows = []
    display_cols = [h for h in raw_headers if not _is_ignored_column(h)]
    for idx, row in df_clean.head(10).iterrows():
        row_dict = {}
        for col in display_cols:
            val = row.get(col)
            if pd.isna(val):
                row_dict[col] = None
            else:
                # If Pandas casted an int column to float because of NaNs, format it cleanly for preview
                if isinstance(val, float) and val.is_integer():
                    row_dict[col] = int(val)
                else:
                    row_dict[col] = val
        sample_rows.append(row_dict)

    # Generate issues
    if not detected_roll:
        issues.append("Roll Number column was not detected.")
    if not detected_name:
        issues.append("Student Name column was not detected.")
    if not detected_admission:
        issues.append(
            "Admission Number column was not found. "
            "SPARSH can still import results — students will be linked manually where required."
        )
    if not detected_subjects:
        issues.append("No subject columns were detected. Manual mapping may be required.")

    # Count actual valid student rows
    total_rows = len(df_clean)

    # Generate workbook signature
    signature = generate_workbook_signature(sheet_name, header_row, headers_clean)

    return SmartAnalysisResult(
        headers_clean=headers_clean,
        total_rows=total_rows,
        detected_header_row=header_row,
        detected_roll_column=detected_roll,
        detected_name_column=detected_name,
        detected_admission_column=detected_admission,
        detected_subjects=detected_subjects,
        sample_rows=sample_rows,
        issues=issues,
        workbook_signature=signature,
        detected_max_marks=normalized_max_marks,
    )


# ============================================
# Parse Excel for Import (Updated)
# ============================================

def parse_excel_for_import(
    file_bytes: bytes,
    sheet_name: str,
    header_row: int,
) -> ParsedExcel:
    """
    Parse a specific worksheet for the import commit step.
    Uses the confirmed sheet name and header row from the analysis step.
    """
    try:
        df = pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name=sheet_name,
            header=header_row,
            engine="openpyxl",
        )
    except Exception as e:
        return ParsedExcel(
            headers=[], rows=[], total_rows=0,
            issues=[f"Failed to read Excel file: {str(e)}"],
        )

    if df.empty:
        return ParsedExcel(
            headers=[], rows=[], total_rows=0,
            issues=["Excel file is empty — no data rows found."],
        )

    # Clean headers
    df.columns = [str(col).strip() for col in df.columns]
    headers = [h for h in df.columns if not _is_ignored_column(h)]

    # Auto-detect identity columns to filter out junk metadata rows
    detected_roll = None
    detected_name = None
    detected_admission_col = None
    
    for col in headers:
        if not detected_roll and _match_identity_column(col, ROLL_HINTS):
            detected_roll = col
        elif not detected_name and _match_identity_column(col, NAME_HINTS):
            detected_name = col
        elif not detected_admission_col and _match_identity_column(col, ADMISSION_HINTS):
            detected_admission_col = col

    # Extract max marks from metadata rows before discarding them
    subject_max_marks = _extract_max_marks(df, df.columns.tolist())

    # Filter out KVS metadata rows at the top and bottom
    df = _filter_junk_rows(df, detected_name, detected_roll, detected_admission_col)

    # Convert rows to dicts
    rows = []
    for idx, row in df.iterrows():
        row_dict = {}
        for col in headers:
            val = row.get(col)
            if pd.isna(val):
                row_dict[col] = None
            else:
                row_dict[col] = val
        rows.append(row_dict)

    return ParsedExcel(
        headers=headers,
        rows=rows,
        total_rows=len(rows),
        detected_admission_column=detected_admission_col,
        subject_max_marks=subject_max_marks,
    )


# ============================================
# Legacy: parse_excel_file (kept for backward compat)
# ============================================

def parse_excel_file(file_bytes: bytes, filename: str) -> ParsedExcel:
    """Legacy parser — delegates to parse_excel_for_import with defaults."""
    sheets = detect_worksheets(file_bytes)
    sheet_name = sheets[0] if sheets else 0
    header_row = detect_header_row(file_bytes, sheet_name) if sheets else 0
    return parse_excel_for_import(file_bytes, sheet_name, header_row)


# ============================================
# Validate and Import (Unchanged core logic)
# ============================================

def validate_and_import(
    db: Session,
    parsed: ParsedExcel,
    academic_year_id: int,
    class_level_id: int,
    section: str,
    exam_id: int,
    column_mappings: list[dict],
    admission_number_column: str | None,
    name_column: str | None,
    roll_number_column: str | None,
    student_mappings: list[dict],
) -> list[RowImportResult]:
    """
    Validate and import parsed Excel rows into the database,
    auto-creating Students and StudentEnrollments as needed.
    """
    results = []

    # Pre-validate: exam exists
    exam = db.query(Exam).filter_by(id=exam_id).first()
    if not exam:
        return [RowImportResult(
            row_number=0, status="error",
            message=f"Exam ID {exam_id} not found.",
        )]

    # Build subject lookup from column mappings
    subject_map: dict[str, Subject] = {}
    for mapping in column_mappings:
        excel_col = mapping["excel_column"]
        subject_id = mapping["subject_id"]
        subject = db.query(Subject).filter_by(id=subject_id).first()
        if not subject:
            return [RowImportResult(
                row_number=0, status="error",
                message=f"Subject ID {subject_id} not found (mapped from column '{excel_col}').",
            )]
        subject_map[excel_col] = subject

    if not subject_map:
        return [RowImportResult(
            row_number=0, status="error",
            message="No column mappings provided. At least one subject column is required.",
        )]

    # Build manual student mapping lookup
    manual_map = {m["row_number"]: m["admission_number"] for m in student_mappings}

    # Process each row
    for row_idx, row_data in enumerate(parsed.rows):
        row_num = row_idx + 2
        row_result = RowImportResult(row_number=row_num)

        # Resolve Identity Columns
        admission_number = None
        extracted_name = None
        extracted_roll = 0

        # Extract Admission Number
        if row_num in manual_map:
            admission_number = str(manual_map[row_num]).strip()
        elif admission_number_column and admission_number_column in row_data:
            raw_val = row_data[admission_number_column]
            if raw_val is not None and str(raw_val).strip().lower() != 'nan':
                admission_number = str(raw_val).strip()
                if admission_number.endswith('.0'):
                    admission_number = admission_number[:-2]

        if not admission_number:
            row_result.status = "skipped"
            row_result.message = "Admission Number column not found. Existing students may be matched manually, but new students cannot be created."
            results.append(row_result)
            continue

        row_result.admission_number = admission_number

        # Extract Name and Roll Number
        if name_column and name_column in row_data:
            raw_name = row_data[name_column]
            if raw_name is not None and str(raw_name).strip().lower() != 'nan':
                extracted_name = str(raw_name).strip()

        if roll_number_column and roll_number_column in row_data:
            raw_roll = row_data[roll_number_column]
            if raw_roll is not None and str(raw_roll).strip().lower() != 'nan':
                try:
                    # Handle floats like 1.0 gracefully
                    extracted_roll = int(float(str(raw_roll).strip()))
                except ValueError:
                    pass

        # Fallback name if missing (rare, but required by DB)
        if not extracted_name:
            extracted_name = f"Unknown Student ({admission_number})"

        # Auto-Create or Match Student
        student = db.query(Student).filter_by(admission_number=admission_number).first()
        
        if not student:
            # CREATE STUDENT
            student = Student(admission_number=admission_number, student_name=extracted_name)
            db.add(student)
            db.flush()
            row_result.student_created = True
            row_result.student_name = extracted_name
        else:
            # EXISTING STUDENT
            row_result.student_matched = True
            row_result.student_name = student.student_name
            # Log warning if names differ significantly
            if extracted_name and extracted_name != f"Unknown Student ({admission_number})":
                if student.student_name.lower() != extracted_name.lower():
                    row_result.message += f"[Note: DB Name '{student.student_name}' differs from Excel '{extracted_name}'] "

        # Auto-Create or Match Enrollment
        enrollment = db.query(StudentEnrollment).filter_by(
            admission_number=admission_number,
            academic_year_id=academic_year_id,
        ).first()

        if not enrollment:
            # CREATE ENROLLMENT
            enrollment = StudentEnrollment(
                admission_number=admission_number,
                academic_year_id=academic_year_id,
                class_level_id=class_level_id,
                section=section,
                roll_number=extracted_roll
            )
            db.add(enrollment)
            db.flush()
            row_result.enrollment_created = True
        else:
            # EXISTING ENROLLMENT (Do not overwrite)
            warnings = []
            if enrollment.class_level_id != class_level_id:
                warnings.append("Class")
            if enrollment.section.lower() != section.lower():
                warnings.append("Section")
            if extracted_roll and enrollment.roll_number != extracted_roll:
                warnings.append("Roll No")
            
            if warnings:
                row_result.message += f"[Note: Excel {', '.join(warnings)} differs from DB enrollment] "

        # Insert Results for Each Mapped Column
        imported_count = 0
        for excel_col, subject in subject_map.items():
            raw_marks = row_data.get(excel_col)

            marks_obtained = None
            grade = None

            if raw_marks is not None:
                raw_str = str(raw_marks).strip()
                if raw_str == "" or raw_str.lower() == "nan":
                    continue

                try:
                    marks_obtained = float(raw_str)
                except ValueError:
                    grade = raw_str
            else:
                continue

            # Check for existing result (prevent duplicate)
            existing_result = db.query(StudentResult).filter_by(
                student_enrollment_id=enrollment.id,
                subject_id=subject.id,
                exam_id=exam_id,
            ).first()

            # Get max marks if extracted during parsing
            subject_max = parsed.subject_max_marks.get(excel_col)

            if existing_result:
                existing_result.marks_obtained = marks_obtained
                existing_result.max_marks = subject_max
                existing_result.grade = grade
            else:
                result = StudentResult(
                    student_enrollment_id=enrollment.id,
                    subject_id=subject.id,
                    exam_id=exam_id,
                    marks_obtained=marks_obtained,
                    max_marks=subject_max,
                    grade=grade,
                )
                db.add(result)

            imported_count += 1

        row_result.results_imported = imported_count
        if imported_count == 0:
            row_result.status = "skipped"
            row_result.message = "No valid marks data found in mapped columns."
        else:
            row_result.status = "ok"
            row_result.message = f"Imported {imported_count} subject result(s)."

        results.append(row_result)

    return results
