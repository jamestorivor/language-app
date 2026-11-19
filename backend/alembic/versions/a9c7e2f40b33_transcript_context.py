"""Retain caption timings and the explicitly selected dictionary form.

Revision ID: a9c7e2f40b33
Revises: f8b5d7c10a22
"""
from alembic import op
import sqlalchemy as sa

revision = "a9c7e2f40b33"
down_revision = "f8b5d7c10a22"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("podcast_transcript", sa.Column("cues", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("study_cards", sa.Column("dictionary_form", sa.Text(), nullable=True))


def downgrade():
    # Caption timings and saved dictionary forms cannot be represented by the
    # prior schema. Never silently discard them when rolling back.
    if op.get_context().as_sql:
        raise RuntimeError("Offline downgrade cannot verify transcript context preservation")
    connection = op.get_bind()
    cues = connection.execute(sa.text("SELECT cues FROM podcast_transcript")).scalars()
    import json
    if any((json.loads(value) if isinstance(value, str) else value) for value in cues):
        raise RuntimeError("Cannot downgrade: transcript cue timing would be lost")
    if connection.execute(sa.text("SELECT 1 FROM study_cards WHERE dictionary_form IS NOT NULL LIMIT 1")).first():
        raise RuntimeError("Cannot downgrade: saved dictionary forms would be lost")
    op.drop_column("study_cards", "dictionary_form")
    op.drop_column("podcast_transcript", "cues")
