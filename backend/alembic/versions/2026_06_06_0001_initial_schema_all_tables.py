"""initial_schema_all_tables

Revision ID: 0001
Revises:
Create Date: 2026-06-06 15:56:57.169607+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Users ---
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # --- Academic Years ---
    op.create_table(
        'academic_years',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('year_label', sa.String(length=20), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('year_label'),
    )

    # --- Class Levels ---
    op.create_table(
        'class_levels',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('class_name', sa.String(length=20), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('class_name'),
    )

    # --- Subjects ---
    op.create_table(
        'subjects',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('subject_name', sa.String(length=100), nullable=False),
        sa.Column('subject_code', sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subject_name'),
        sa.UniqueConstraint('subject_code'),
    )

    # --- Exams ---
    op.create_table(
        'exams',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exam_name', sa.String(length=50), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exam_name'),
    )

    # --- Students ---
    op.create_table(
        'students',
        sa.Column('admission_number', sa.String(length=20), nullable=False),
        sa.Column('student_name', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('admission_number'),
    )

    # --- Student Enrollments ---
    op.create_table(
        'student_enrollments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('admission_number', sa.String(length=20), nullable=False),
        sa.Column('academic_year_id', sa.Integer(), nullable=False),
        sa.Column('class_level_id', sa.Integer(), nullable=False),
        sa.Column('section', sa.String(length=5), nullable=False),
        sa.Column('roll_number', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['admission_number'], ['students.admission_number']),
        sa.ForeignKeyConstraint(['academic_year_id'], ['academic_years.id']),
        sa.ForeignKeyConstraint(['class_level_id'], ['class_levels.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('admission_number', 'academic_year_id', name='uq_student_year_enrollment'),
    )
    op.create_index('ix_student_enrollments_admission_number', 'student_enrollments', ['admission_number'])

    # --- Student Results ---
    op.create_table(
        'student_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('student_enrollment_id', sa.Integer(), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('marks_obtained', sa.Float(), nullable=True),
        sa.Column('max_marks', sa.Float(), nullable=True),
        sa.Column('grade', sa.String(length=5), nullable=True),
        sa.ForeignKeyConstraint(['student_enrollment_id'], ['student_enrollments.id']),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id']),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_enrollment_id', 'subject_id', 'exam_id', name='uq_enrollment_subject_exam'),
    )
    op.create_index('ix_student_results_enrollment', 'student_results', ['student_enrollment_id'])

    # --- Historical Reports ---
    op.create_table(
        'historical_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('admission_number', sa.String(length=20), nullable=False),
        sa.Column('academic_year_id', sa.Integer(), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('storage_provider', sa.String(length=30), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['admission_number'], ['students.admission_number']),
        sa.ForeignKeyConstraint(['academic_year_id'], ['academic_years.id']),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_historical_reports_admission_number', 'historical_reports', ['admission_number'])


def downgrade() -> None:
    op.drop_table('historical_reports')
    op.drop_table('student_results')
    op.drop_table('student_enrollments')
    op.drop_table('students')
    op.drop_table('exams')
    op.drop_table('subjects')
    op.drop_table('class_levels')
    op.drop_table('academic_years')
    op.drop_table('users')
