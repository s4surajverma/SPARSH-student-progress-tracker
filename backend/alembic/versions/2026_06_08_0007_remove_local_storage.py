"""migrate_local_to_google_drive

Revision ID: 0007_remove_local
Revises: 0006_oauth
Create Date: 2026-06-08

Updates any existing app_settings rows with storage_provider='local' to 'google_drive'.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0007_remove_local'
down_revision = '0006_oauth'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update any existing rows that still have 'local' as the provider
    op.execute(
        "UPDATE app_settings SET storage_provider = 'google_drive' WHERE storage_provider = 'local'"
    )


def downgrade() -> None:
    # No-op: we don't want to re-introduce 'local'
    pass
