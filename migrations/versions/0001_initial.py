"""Initial migration baseline; application tables follow in sprint 0.2."""

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Establish the baseline revision for subsequent schema changes."""


def downgrade() -> None:
    """The baseline has no schema objects to remove."""
