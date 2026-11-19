"""Ask new accounts to choose a learning language.

Revision ID: b4d9f2a7c103
Revises: ab73d5e80120
"""
from alembic import op
import sqlalchemy as sa

revision = "b4d9f2a7c103"
down_revision = "ab73d5e80120"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("learning_language_selected", sa.Boolean(), nullable=True))
    # Existing accounts already have a preference, including the previous default.
    op.execute(sa.text("UPDATE users SET learning_language_selected = true"))


def downgrade():
    op.drop_column("users", "learning_language_selected")
