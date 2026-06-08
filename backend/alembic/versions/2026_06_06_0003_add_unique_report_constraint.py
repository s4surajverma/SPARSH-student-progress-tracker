"""add_unique_report_constraint

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-06

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('historical_reports', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'uq_report_student_year',
            ['admission_number', 'academic_year_id'],
        )


def downgrade() -> None:
    with op.batch_alter_table('historical_reports', schema=None) as batch_op:
        batch_op.drop_constraint('uq_report_student_year', type_='unique')
