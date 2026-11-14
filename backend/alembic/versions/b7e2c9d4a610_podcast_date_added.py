"""Record when podcast episodes are added.

Revision ID: b7e2c9d4a610
Revises: f4b5c6d7e8f9
"""
from alembic import op
import sqlalchemy as sa

revision = "b7e2c9d4a610"
down_revision = "f4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade():
    # Existing episodes have no reliable creation timestamp.
    op.add_column("podcasts", sa.Column("added_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("podcasts", "added_at", server_default=sa.func.now())


def downgrade():
    op.drop_column("podcasts", "added_at")
