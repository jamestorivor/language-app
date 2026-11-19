"""Store basic FSRS preferences on each user.

Revision ID: b1c2d3e4f501
Revises: a9c7e2f40b33
"""
from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f501"
down_revision = "a9c7e2f40b33"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("fsrs_retention_percent", sa.Integer(), nullable=False, server_default="90"))
    op.add_column("users", sa.Column("fsrs_maximum_interval", sa.Integer(), nullable=False, server_default="36500"))
    op.add_column("users", sa.Column("fsrs_fuzzing", sa.Boolean(), nullable=False, server_default=sa.text("true")))


def downgrade():
    op.drop_column("users", "fsrs_fuzzing")
    op.drop_column("users", "fsrs_maximum_interval")
    op.drop_column("users", "fsrs_retention_percent")
