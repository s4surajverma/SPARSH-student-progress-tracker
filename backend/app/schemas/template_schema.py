"""
School Result Analysis System - Import Template Schemas
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ColumnMapping(BaseModel):
    excel_column: str
    subject_id: int


class TemplateCreate(BaseModel):
    template_name: str
    mapping_json: list[ColumnMapping]


class TemplateResponse(BaseModel):
    id: int
    template_name: str
    mapping_json: list[ColumnMapping]
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
