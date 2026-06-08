"""
School Result Analysis System - Import Template Model

Stores reusable column mapping configurations for Excel imports.
Allows teachers to map columns once and reuse the template for
future imports of similar Excel files.
"""

from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ImportTemplate(Base):
    __tablename__ = "import_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    
    # Store the mapping structure as JSON: [{"excel_column": "Maths", "subject_id": 3}, ...]
    mapping_json: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    
    # Metadata
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<ImportTemplate(id={self.id}, name='{self.template_name}')>"
