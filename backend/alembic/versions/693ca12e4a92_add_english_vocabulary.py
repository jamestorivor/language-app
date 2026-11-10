"""Add English dictionary and familiarity tracking.

Revision ID: 693ca12e4a92
Revises: 3d6545e856d6
"""
from alembic import op
import sqlalchemy as sa

revision = "693ca12e4a92"
down_revision = "3d6545e856d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "english_dictionary",
        sa.Column("word_id", sa.Integer(), primary_key=True),
        sa.Column("headword", sa.Text(), nullable=False, unique=True),
        sa.Column("lookup_key", sa.Text(), nullable=False),
        sa.Column("meaning", sa.Text(), nullable=False),
    )
    op.create_index("ix_english_dictionary_lookup_key", "english_dictionary", ["lookup_key"])
    op.create_table(
        "user_english_word_progress",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("english_dictionary.word_id"), primary_key=True),
        sa.Column("familiarity_score", sa.Integer(), nullable=False),
        sa.CheckConstraint("familiarity_score BETWEEN 1 AND 5", name="valid_english_familiarity_score"),
    )


def downgrade() -> None:
    op.drop_table("user_english_word_progress")
    op.drop_index("ix_english_dictionary_lookup_key", table_name="english_dictionary")
    op.drop_table("english_dictionary")
