"""add outfit templates, outfits, and the wear log

Revision ID: d378dfb81d37
Revises: dd188a82ec8e
Create Date: 2026-10-15 20:26:08.048276
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d378dfb81d37"
down_revision: str | Sequence[str] | None = "dd188a82ec8e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outfit_templates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("required", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("optional", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outfit_templates")),
    )
    op.create_table(
        "outfits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("template_id", sa.String(), nullable=True),
        sa.Column("occasion_id", sa.String(), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["occasion_id"], ["occasions.id"], name=op.f("fk_outfits_occasion_id_occasions")
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["outfit_templates.id"],
            name=op.f("fk_outfits_template_id_outfit_templates"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_outfits_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outfits")),
    )
    op.create_index(op.f("ix_outfits_user_id"), "outfits", ["user_id"], unique=False)
    op.create_table(
        "wear_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("worn_on", sa.Date(), nullable=False),
        sa.Column("outfit_id", sa.Uuid(), nullable=True),
        sa.Column("occasion_id", sa.String(), nullable=True),
        sa.Column("note", sa.String(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["occasion_id"], ["occasions.id"], name=op.f("fk_wear_logs_occasion_id_occasions")
        ),
        sa.ForeignKeyConstraint(
            ["outfit_id"],
            ["outfits.id"],
            name=op.f("fk_wear_logs_outfit_id_outfits"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_wear_logs_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wear_logs")),
    )
    op.create_index(op.f("ix_wear_logs_outfit_id"), "wear_logs", ["outfit_id"], unique=False)
    op.create_index(
        "ix_wear_logs_user_id_worn_on", "wear_logs", ["user_id", "worn_on"], unique=False
    )
    op.create_table(
        "outfit_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("outfit_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=True),
        sa.Column("slot", sa.String(), nullable=False),
        sa.Column("item_name", sa.String(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name=op.f("fk_outfit_items_item_id_items"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["outfit_id"],
            ["outfits.id"],
            name=op.f("fk_outfit_items_outfit_id_outfits"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outfit_items")),
    )
    op.create_index(op.f("ix_outfit_items_item_id"), "outfit_items", ["item_id"], unique=False)
    op.create_index(
        "uq_outfit_items_outfit_id_slot", "outfit_items", ["outfit_id", "slot"], unique=True
    )
    op.create_table(
        "wear_log_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("wear_log_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=True),
        sa.Column("slot", sa.String(), nullable=False),
        sa.Column("item_name", sa.String(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name=op.f("fk_wear_log_items_item_id_items"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["wear_log_id"],
            ["wear_logs.id"],
            name=op.f("fk_wear_log_items_wear_log_id_wear_logs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wear_log_items")),
    )
    op.create_index(op.f("ix_wear_log_items_item_id"), "wear_log_items", ["item_id"], unique=False)
    op.create_index(
        "uq_wear_log_items_wear_log_id_item_id",
        "wear_log_items",
        ["wear_log_id", "item_id"],
        unique=True,
    )
    op.add_column("items", sa.Column("last_washed_on", sa.Date(), nullable=True))
    op.add_column("vocabulary_terms", sa.Column("role", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("vocabulary_terms", "role")
    op.drop_column("items", "last_washed_on")
    op.drop_index("uq_wear_log_items_wear_log_id_item_id", table_name="wear_log_items")
    op.drop_index(op.f("ix_wear_log_items_item_id"), table_name="wear_log_items")
    op.drop_table("wear_log_items")
    op.drop_index("uq_outfit_items_outfit_id_slot", table_name="outfit_items")
    op.drop_index(op.f("ix_outfit_items_item_id"), table_name="outfit_items")
    op.drop_table("outfit_items")
    op.drop_index("ix_wear_logs_user_id_worn_on", table_name="wear_logs")
    op.drop_index(op.f("ix_wear_logs_outfit_id"), table_name="wear_logs")
    op.drop_table("wear_logs")
    op.drop_index(op.f("ix_outfits_user_id"), table_name="outfits")
    op.drop_table("outfits")
    op.drop_table("outfit_templates")
