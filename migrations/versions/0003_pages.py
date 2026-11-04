"""Add hierarchical wiki pages."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_pages"
down_revision: str | None = "0002_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column(
            "author_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pages_path", "pages", ["path"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_pages_path", table_name="pages")
    op.drop_table("pages")
