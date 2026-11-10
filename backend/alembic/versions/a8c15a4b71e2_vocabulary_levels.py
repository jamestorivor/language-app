"""Add and populate approximate JLPT and CEFR dictionary levels.

Revision ID: a8c15a4b71e2
Revises: 2ba81ce49f51
"""
from alembic import op
import sqlalchemy as sa

from app.db.vocabulary_levels import english_levels, japanese_levels

revision = "a8c15a4b71e2"
down_revision = "2ba81ce49f51"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("japanese_dictionary", sa.Column("jlpt_level", sa.Text(), nullable=True))
    op.add_column("english_dictionary", sa.Column("cefr_level", sa.Text(), nullable=True))
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE japanese_dictionary SET jlpt_level = :level WHERE source_entry_id = :entry"),
        [{"entry": entry, "level": level} for entry, level in japanese_levels().items()],
    )
    connection.execute(
        sa.text("UPDATE english_dictionary SET cefr_level = :level WHERE lookup_key = :entry"),
        [{"entry": entry, "level": level} for entry, level in english_levels().items()],
    )


def downgrade() -> None:
    op.drop_column("english_dictionary", "cefr_level")
    op.drop_column("japanese_dictionary", "jlpt_level")
