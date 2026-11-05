"""Require user profile names and track the last page editor."""

import sqlalchemy as sa
from alembic import op

from app.auth.usernames import canonicalize_username
from app.config import get_settings

revision = "0006_user_profiles"
down_revision = "0005_auth_public"
branch_labels = None
depends_on = None


def upgrade() -> None:
    settings = get_settings()
    op.add_column("users", sa.Column("first_name", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(100), nullable=True))

    bind = op.get_bind()
    users = bind.execute(sa.text("SELECT id, username, role FROM users")).all()
    matches = [
        row
        for row in users
        if canonicalize_username(row.username)
        == canonicalize_username(settings.admin_username)
        and row.role == "admin"
    ]
    if len(matches) == 1:
        bind.execute(
            sa.text(
                "UPDATE users SET first_name = :first_name, last_name = :last_name WHERE id = :user_id"
            ),
            {
                "first_name": settings.admin_first_name,
                "last_name": settings.admin_last_name,
                "user_id": matches[0].id,
            },
        )
    missing_names = bind.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM users WHERE first_name IS NULL OR last_name IS NULL)"
        )
    )
    if missing_names:
        raise RuntimeError(
            "User profile migration requires names for every existing account."
        )

    op.alter_column("users", "first_name", nullable=False)
    op.alter_column("users", "last_name", nullable=False)
    op.create_check_constraint(
        "ck_users_first_name", "users", "length(btrim(first_name)) > 0"
    )
    op.create_check_constraint(
        "ck_users_last_name", "users", "length(btrim(last_name)) > 0"
    )

    op.add_column("pages", sa.Column("last_editor_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_pages_last_editor_id_users",
        "pages",
        "users",
        ["last_editor_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_pages_last_editor_id_users", "pages", type_="foreignkey")
    op.drop_column("pages", "last_editor_id")
    op.drop_constraint("ck_users_last_name", "users", type_="check")
    op.drop_constraint("ck_users_first_name", "users", type_="check")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
