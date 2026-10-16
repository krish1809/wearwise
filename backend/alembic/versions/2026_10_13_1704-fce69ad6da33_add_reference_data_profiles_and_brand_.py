"""add reference data, profiles, and brand notes

Revision ID: fce69ad6da33
Revises: b7ae839ae206
Create Date: 2026-10-13 17:04:13.238174
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "fce69ad6da33"
down_revision: str | Sequence[str] | None = "b7ae839ae206"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "category_groups",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_category_groups")),
    )
    op.create_table(
        "color_families",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("hex", sa.String(), nullable=True),
        sa.Column("neutrality", sa.Double(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_color_families")),
    )
    op.create_table(
        "occasions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("formality_min", sa.Integer(), nullable=False),
        sa.Column("formality_max", sa.Integer(), nullable=False),
        sa.Column(
            "prefers_groups", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False
        ),
        sa.Column("hint", sa.String(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_occasions")),
    )
    op.create_table(
        "style_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("signals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_style_profiles")),
    )
    op.create_table(
        "vocabulary_terms",
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
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
        sa.PrimaryKeyConstraint("kind", "id", name=op.f("pk_vocabulary_terms")),
    )
    op.create_table(
        "brand_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("brand", sa.String(), nullable=False),
        sa.Column("size_notes", sa.String(), nullable=True),
        sa.Column("quality_notes", sa.String(), nullable=True),
        sa.Column("price_notes", sa.String(), nullable=True),
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
            ["user_id"], ["users.id"], name=op.f("fk_brand_notes_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_brand_notes")),
    )
    op.create_index(
        "uq_brand_notes_user_id_brand",
        "brand_notes",
        ["user_id", sa.literal_column("lower(brand)")],
        unique=True,
    )
    op.create_table(
        "profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("sections", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("units", sa.String(), server_default="cm", nullable=False),
        sa.Column("currency", sa.String(), server_default="INR", nullable=False),
        sa.Column("height_cm", sa.Double(), nullable=True),
        sa.Column(
            "measurements",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "sizes", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("fit_preference", sa.String(), nullable=True),
        sa.Column(
            "style_profile_ids", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False
        ),
        sa.Column(
            "preferred_colors", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False
        ),
        sa.Column(
            "avoided_colors", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False
        ),
        sa.Column(
            "occasion_ids", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False
        ),
        sa.Column("budget_monthly", sa.BigInteger(), nullable=True),
        sa.Column(
            "category_budgets",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("onboarding_step", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column(
            "onboarding_skipped", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("onboarding_reminder_dismissed_at", sa.DateTime(timezone=True), nullable=True),
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
            ["user_id"], ["users.id"], name=op.f("fk_profiles_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_profiles_user_id")),
    )


def downgrade() -> None:
    op.drop_table("profiles")
    op.drop_index("uq_brand_notes_user_id_brand", table_name="brand_notes")
    op.drop_table("brand_notes")
    op.drop_table("vocabulary_terms")
    op.drop_table("style_profiles")
    op.drop_table("occasions")
    op.drop_table("color_families")
    op.drop_table("category_groups")
