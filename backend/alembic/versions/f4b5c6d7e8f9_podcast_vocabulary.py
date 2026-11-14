"""Store vocabulary baselines and cached transcript analyses.

Revision ID: f4b5c6d7e8f9
Revises: a8c15a4b71e2
"""
from alembic import op
import sqlalchemy as sa

revision = "f4b5c6d7e8f9"
down_revision = "a8c15a4b71e2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("podcast_vocabulary_baseline",
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("podcasts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("language", sa.String(2), nullable=False),
        sa.Column("scores", sa.JSON(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_podcast_vocabulary_baseline_user_id", "podcast_vocabulary_baseline", ["user_id"])
    op.create_table("podcast_vocabulary_analysis",
        sa.Column("chunk_id", sa.Integer(), sa.ForeignKey("podcast_chunk.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("counts", sa.JSON(), nullable=False),
        sa.Column("unmatched", sa.Integer(), nullable=False))


def downgrade():
    op.drop_table("podcast_vocabulary_analysis")
    op.drop_index("ix_podcast_vocabulary_baseline_user_id", table_name="podcast_vocabulary_baseline")
    op.drop_table("podcast_vocabulary_baseline")
