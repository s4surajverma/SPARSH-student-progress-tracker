"""replace_service_account_with_oauth

Revision ID: 0006_oauth
Revises: 2d944c71a398
Create Date: 2026-06-07

Drops the Service Account credential columns and adds OAuth credential columns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006_oauth'
down_revision: Union[str, None] = '2d944c71a398'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new OAuth columns
    op.add_column('app_settings', sa.Column('google_oauth_refresh_token_encrypted', sa.String(), nullable=True))
    op.add_column('app_settings', sa.Column('google_user_email', sa.String(length=255), nullable=True))

    # Drop old Service Account columns
    op.drop_column('app_settings', 'gcp_service_account_json')
    op.drop_column('app_settings', 'gcp_credentials_encrypted')
    op.drop_column('app_settings', 'service_account_email')


def downgrade() -> None:
    # Re-add old Service Account columns
    op.add_column('app_settings', sa.Column('service_account_email', sa.String(length=255), nullable=True))
    op.add_column('app_settings', sa.Column('gcp_credentials_encrypted', sa.String(), nullable=True))
    op.add_column('app_settings', sa.Column('gcp_service_account_json', sa.JSON(), nullable=True))

    # Drop new OAuth columns
    op.drop_column('app_settings', 'google_user_email')
    op.drop_column('app_settings', 'google_oauth_refresh_token_encrypted')
