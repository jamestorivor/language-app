"""Allow words to be marked as not planned for learning.

Revision ID: c9d3e4f5a6b7
Revises: b7e2c9d4a610
"""
from alembic import op

revision = "c9d3e4f5a6b7"
down_revision = "b7e2c9d4a610"
branch_labels = None
depends_on = None

CONSTRAINTS = (
    ("user_japanese_word_progress", "valid_familiarity_score"),
    ("user_english_word_progress", "valid_english_familiarity_score"),
)


def upgrade() -> None:
    for table, name in CONSTRAINTS:
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, "familiarity_score = -1 OR familiarity_score BETWEEN 1 AND 5")


def downgrade() -> None:
    for table, name in CONSTRAINTS:
        # Earlier versions have no representation for this state; make such words unrated.
        op.execute(f"DELETE FROM {table} WHERE familiarity_score = -1")
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, "familiarity_score BETWEEN 1 AND 5")
