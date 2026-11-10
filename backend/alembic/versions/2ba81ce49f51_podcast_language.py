"""Store each podcast's language.

Revision ID: 2ba81ce49f51
Revises: 693ca12e4a92
"""
from alembic import op
import sqlalchemy as sa

revision = "2ba81ce49f51"
down_revision = "693ca12e4a92"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("podcasts", sa.Column("language", sa.String(2), server_default="ja", nullable=False))
    op.create_check_constraint("valid_podcast_language", "podcasts", "language IN ('ja', 'en')")


def downgrade() -> None:
    op.drop_constraint("valid_podcast_language", "podcasts", type_="check")
    op.drop_column("podcasts", "language")
