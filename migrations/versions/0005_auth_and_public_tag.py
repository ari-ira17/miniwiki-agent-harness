"""Add server sessions and make public tag canonical."""

import sqlalchemy as sa
from alembic import op

revision = "0005_auth_public"
down_revision = "0004_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
    )
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    op.execute(
        """
        INSERT INTO tags (name)
        SELECT 'public'
        WHERE EXISTS (SELECT 1 FROM pages WHERE is_public IS TRUE)
        ON CONFLICT (name) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO page_tags (page_id, tag_id)
        SELECT pages.id, tags.id
        FROM pages CROSS JOIN tags
        WHERE pages.is_public IS TRUE AND tags.name = 'public'
        ON CONFLICT DO NOTHING
        """
    )
    op.drop_column("pages", "is_public")


def downgrade() -> None:
    op.add_column(
        "pages",
        sa.Column("is_public", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.execute(
        """
        UPDATE pages SET is_public = TRUE
        WHERE id IN (
            SELECT page_id FROM page_tags
            JOIN tags ON tags.id = page_tags.tag_id WHERE tags.name = 'public'
        )
        """
    )
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_table("auth_sessions")
