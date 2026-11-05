"""User identity and role model."""

from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserRole(StrEnum):
    ADMIN = "admin"
    EDITOR = "editor"
    READER = "reader"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(btrim(first_name)) > 0", name="ck_users_first_name"),
        CheckConstraint("length(btrim(last_name)) > 0", name="ck_users_last_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            create_constraint=True,
            length=16,
            values_callable=lambda roles: [role.value for role in roles],
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
