"""Store self-reported levels separately for each language.

Revision ID: c6f28a17d345
Revises: b4d9f2a7c103
"""
from alembic import op
import sqlalchemy as sa

revision = "c6f28a17d345"
down_revision = "b4d9f2a7c103"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("japanese_level", sa.String(2), nullable=True))
    op.add_column("users", sa.Column("english_level", sa.String(2), nullable=True))


def downgrade():
    if op.get_context().as_sql:
        raise RuntimeError("Offline downgrade cannot verify saved levels")
    if op.get_bind().execute(sa.text("SELECT 1 FROM users WHERE japanese_level IS NOT NULL OR english_level IS NOT NULL LIMIT 1")).first():
        raise RuntimeError("Cannot downgrade while saved levels exist")
    op.drop_column("users", "english_level")
    op.drop_column("users", "japanese_level")
