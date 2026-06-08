"""add_import_templates_table

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('import_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('template_name', sa.String(length=100), nullable=False),
        sa.Column('mapping_json', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_import_templates_template_name'), 'import_templates', ['template_name'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_import_templates_template_name'), table_name='import_templates')
    op.drop_table('import_templates')
