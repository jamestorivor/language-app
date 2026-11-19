"""Add explicitly selected sentence cards and their review history.

Revision ID: d2e6f8a9b001
Revises: c9d3e4f5a6b7
"""
from alembic import op
import sqlalchemy as sa

revision = "d2e6f8a9b001"
down_revision = "c9d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "study_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("japanese_dictionary.word_id"), nullable=False),
        sa.Column("occurrence_key", sa.String(64), nullable=False),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("podcasts.id", ondelete="SET NULL")),
        sa.Column("segment_id", sa.Integer(), sa.ForeignKey("podcast_chunk.id", ondelete="SET NULL")),
        sa.Column("episode_title", sa.Text()),
        sa.Column("sentence", sa.Text(), nullable=False),
        sa.Column("target_text", sa.Text(), nullable=False),
        sa.Column("reading", sa.Text(), nullable=False),
        sa.Column("definitions", sa.JSON(), nullable=False),
        sa.Column("sentence_start", sa.Integer(), nullable=False),
        sa.Column("sentence_end", sa.Integer(), nullable=False),
        sa.Column("target_start", sa.Integer(), nullable=False),
        sa.Column("target_end", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fsrs_card", sa.JSON(), nullable=False),
        sa.Column("scheduler_version", sa.String(40), nullable=False),
        sa.Column("scheduler_config", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "occurrence_key", name="uq_study_card_occurrence"),
    )
    op.create_index("ix_study_cards_user_due", "study_cards", ["user_id", "due_at"])
    op.create_table(
        "study_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("card_id", sa.Integer(), sa.ForeignKey("study_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("before_state", sa.JSON(), nullable=False),
        sa.Column("after_state", sa.JSON(), nullable=False),
        sa.Column("review_log", sa.JSON(), nullable=False),
        sa.Column("scheduler_version", sa.String(40), nullable=False),
    )
    op.create_index("ix_study_reviews_card_id", "study_reviews", ["card_id"])


def downgrade():
    op.drop_table("study_reviews")
    op.drop_table("study_cards")
