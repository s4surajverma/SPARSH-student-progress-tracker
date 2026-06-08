"""add_import_batches_table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-06 16:44:55.381071+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'import_batches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('academic_year_id', sa.Integer(), nullable=False),
        sa.Column('class_level_id', sa.Integer(), nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('section', sa.String(length=5), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='completed'),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('imported_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['academic_year_id'], ['academic_years.id']),
        sa.ForeignKeyConstraint(['class_level_id'], ['class_levels.id']),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id']),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('import_batches')
