"""
School Result Analysis System - Import Template APIs
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.user import User
from app.models.template import ImportTemplate
from app.schemas.template_schema import TemplateCreate, TemplateResponse

router = APIRouter()

# Templates can be read by all, but only managed by admins/teachers
WRITE_ROLES = ["admin", "teacher"]


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*WRITE_ROLES)),
):
    """Create a new reusable column mapping template."""
    # Check for duplicate name
    existing = db.query(ImportTemplate).filter_by(template_name=payload.template_name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template with name '{payload.template_name}' already exists."
        )

    # Convert mapping_json Pydantic models to dicts for JSON column
    mapping_data = [m.model_dump() for m in payload.mapping_json]

    template = ImportTemplate(
        template_name=payload.template_name,
        mapping_json=mapping_data,
        created_by=current_user.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/", response_model=list[TemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher", "principal")),
):
    """List all available templates."""
    return db.query(ImportTemplate).order_by(ImportTemplate.template_name).all()


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher", "principal")),
):
    """Get a specific template by ID."""
    template = db.query(ImportTemplate).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found.")
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*WRITE_ROLES)),
):
    """Delete a template."""
    template = db.query(ImportTemplate).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found.")
    
    db.delete(template)
    db.commit()
