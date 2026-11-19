"""Persist review keyboard shortcuts.

Revision ID: d9e2c68a315f
Revises: c4e18a9d6f20
"""
from alembic import op
import sqlalchemy as sa

revision = "d9e2c68a315f"
down_revision = "c4e18a9d6f20"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("study_shortcuts", sa.JSON(), nullable=True))


def downgrade():
    if op.get_context().as_sql:
        raise RuntimeError("Offline downgrade cannot verify shortcut preservation")
    if op.get_bind().execute(sa.text("SELECT 1 FROM users WHERE study_shortcuts IS NOT NULL LIMIT 1")).first():
        raise RuntimeError("Cannot downgrade while custom study shortcuts exist")
    op.drop_column("users", "study_shortcuts")
