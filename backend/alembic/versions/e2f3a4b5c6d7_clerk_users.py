"""Associate local users with Clerk accounts.

Revision ID: e2f3a4b5c6d7
Revises: d9e2c68a315f
"""
from alembic import op
import sqlalchemy as sa

revision = "e2f3a4b5c6d7"
down_revision = "d9e2c68a315f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("clerk_id", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_clerk_id", "users", ["clerk_id"])


def downgrade():
    op.drop_constraint("uq_users_clerk_id", "users", type_="unique")
    op.drop_column("users", "clerk_id")
