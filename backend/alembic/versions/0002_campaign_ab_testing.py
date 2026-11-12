"""Track whether a published campaign is rotating popup versions."""

from alembic import op
import sqlalchemy as sa

revision = "0002_campaign_ab_testing"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column(
            "ab_test_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("campaigns", "ab_test_enabled")