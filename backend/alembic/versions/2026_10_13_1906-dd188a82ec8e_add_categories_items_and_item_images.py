"""add categories, items, and item images

Revision ID: dd188a82ec8e
Revises: fce69ad6da33
Create Date: 2026-10-13 19:06:44.028807
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "dd188a82ec8e"
down_revision: str | Sequence[str] | None = "fce69ad6da33"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("slot", sa.String(), nullable=False),
        sa.Column("sections", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("formality_default", sa.Integer(), nullable=False),
        sa.Column("formality_min", sa.Integer(), nullable=False),
        sa.Column("formality_max", sa.Integer(), nullable=False),
        sa.Column("warmth", sa.Integer(), nullable=False),
        sa.Column("wears_before_wash", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["category_groups.id"],
            name=op.f("fk_categories_group_id_category_groups"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_categories_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
    )
    op.create_index(op.f("ix_categories_user_id"), "categories", ["user_id"], unique=False)
    op.create_index(
        "uq_categories_user_id_name",
        "categories",
        ["user_id", sa.literal_column("lower(name)")],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_table(
        "items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.String(), nullable=False),
        sa.Column("slot", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("brand", sa.String(), nullable=True),
        sa.Column("size_label", sa.String(), nullable=True),
        sa.Column("color_primary", sa.String(), nullable=False),
        sa.Column("color_secondary", sa.String(), nullable=True),
        sa.Column("color_hex", sa.String(), nullable=True),
        sa.Column("pattern", sa.String(), server_default="solid", nullable=False),
        sa.Column("fabric", sa.String(), nullable=True),
        sa.Column("fit", sa.String(), nullable=True),
        sa.Column("formality", sa.SmallInteger(), nullable=False),
        sa.Column("warmth", sa.SmallInteger(), nullable=False),
        sa.Column("seasons", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column(
            "occasion_ids", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False
        ),
        sa.Column("style_tags", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("price", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(), server_default="INR", nullable=False),
        sa.Column("purchased_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(), server_default="available", nullable=False),
        sa.Column("wears_before_wash", sa.SmallInteger(), nullable=True),
        sa.Column("wears_since_wash", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("set_id", sa.Uuid(), nullable=True),
        sa.Column(
            "attrs", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
            ["category_id"], ["categories.id"], name=op.f("fk_items_category_id_categories")
        ),
        sa.ForeignKeyConstraint(
            ["color_primary"],
            ["color_families.id"],
            name=op.f("fk_items_color_primary_color_families"),
        ),
        sa.ForeignKeyConstraint(
            ["color_secondary"],
            ["color_families.id"],
            name=op.f("fk_items_color_secondary_color_families"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_items_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_items")),
    )
    op.create_index(
        "ix_items_occasion_ids", "items", ["occasion_ids"], unique=False, postgresql_using="gin"
    )
    op.create_index("ix_items_seasons", "items", ["seasons"], unique=False, postgresql_using="gin")
    op.create_index(op.f("ix_items_set_id"), "items", ["set_id"], unique=False)
    op.create_index(
        "ix_items_style_tags", "items", ["style_tags"], unique=False, postgresql_using="gin"
    )
    op.create_index(
        "ix_items_user_id_archived_at", "items", ["user_id", "archived_at"], unique=False
    )
    op.create_index(
        "ix_items_user_id_category_id", "items", ["user_id", "category_id"], unique=False
    )
    op.create_index("ix_items_user_id_created_at", "items", ["user_id", "created_at"], unique=False)
    op.create_index("ix_items_user_id_slot", "items", ["user_id", "slot"], unique=False)
    op.create_table(
        "item_images",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=True),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("thumb_key", sa.String(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("dominant_hex", sa.String(), nullable=True),
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
            ["item_id"], ["items.id"], name=op.f("fk_item_images_item_id_items"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_item_images_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_item_images")),
    )
    op.create_index(op.f("ix_item_images_item_id"), "item_images", ["item_id"], unique=False)
    op.create_index(op.f("ix_item_images_user_id"), "item_images", ["user_id"], unique=False)
    op.add_column(
        "users", sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("users", "is_demo")
    op.drop_index(op.f("ix_item_images_user_id"), table_name="item_images")
    op.drop_index(op.f("ix_item_images_item_id"), table_name="item_images")
    op.drop_table("item_images")
    op.drop_index("ix_items_user_id_slot", table_name="items")
    op.drop_index("ix_items_user_id_created_at", table_name="items")
    op.drop_index("ix_items_user_id_category_id", table_name="items")
    op.drop_index("ix_items_user_id_archived_at", table_name="items")
    op.drop_index("ix_items_style_tags", table_name="items", postgresql_using="gin")
    op.drop_index(op.f("ix_items_set_id"), table_name="items")
    op.drop_index("ix_items_seasons", table_name="items", postgresql_using="gin")
    op.drop_index("ix_items_occasion_ids", table_name="items", postgresql_using="gin")
    op.drop_table("items")
    op.drop_index(
        "uq_categories_user_id_name",
        table_name="categories",
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.drop_index(op.f("ix_categories_user_id"), table_name="categories")
    op.drop_table("categories")
