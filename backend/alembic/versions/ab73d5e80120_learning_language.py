"""Save the account's learning language.

Revision ID: ab73d5e80120
Revises: e2f3a4b5c6d7
"""
from alembic import op
import sqlalchemy as sa

revision = "ab73d5e80120"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("learning_language", sa.String(2), nullable=False, server_default="ja"))


def downgrade():
    if op.get_context().as_sql:
        raise RuntimeError("Offline downgrade cannot verify learning language preservation")
    if op.get_bind().execute(sa.text("SELECT 1 FROM users WHERE learning_language != 'ja' LIMIT 1")).first():
        raise RuntimeError("Cannot downgrade while learning language preferences exist")
    op.drop_column("users", "learning_language")
