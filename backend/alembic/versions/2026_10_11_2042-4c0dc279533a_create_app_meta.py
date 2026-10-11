"""create app_meta

Revision ID: 4c0dc279533a
Revises:
Create Date: 2026-10-11 20:42:38.231272
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4c0dc279533a"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    app_meta = op.create_table(
        "app_meta",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_app_meta")),
        sa.UniqueConstraint("key", name=op.f("uq_app_meta_key")),
    )
    # The health check reads this row to confirm the database is reachable and migrated.
    op.bulk_insert(app_meta, [{"id": uuid.uuid7(), "key": "app", "value": "wearwise"}])


def downgrade() -> None:
    op.drop_table("app_meta")
