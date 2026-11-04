"""Add page tags and associations."""

import sqlalchemy as sa
from alembic import op

revision = "0004_tags"
down_revision = "0003_pages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("name", name="uq_tags_name"),
    )
    op.create_table(
        "page_tags",
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["page_id"], ["pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("page_id", "tag_id"),
    )


def downgrade() -> None:
    op.drop_table("page_tags")
    op.drop_table("tags")
