"""add suggestions, their feedback, and engine fields on outfits

Revision ID: 9f8e8bba4f36
Revises: d378dfb81d37
Create Date: 2026-10-16 07:03:06.728929
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9f8e8bba4f36"
down_revision: str | Sequence[str] | None = "d378dfb81d37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "suggestions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("occasion_id", sa.String(), nullable=True),
        sa.Column("season", sa.String(), nullable=True),
        sa.Column("template_id", sa.String(), nullable=False),
        sa.Column("item_ids", postgresql.ARRAY(sa.Uuid()), nullable=False),
        sa.Column("core_ids", postgresql.ARRAY(sa.Uuid()), nullable=False),
        sa.Column("score", sa.Double(), nullable=False),
        sa.Column("components", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("compromise", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("engine_version", sa.String(), nullable=False),
        sa.Column("rating", sa.String(), nullable=True),
        sa.Column("saved_outfit_id", sa.Uuid(), nullable=True),
        sa.Column("wear_log_id", sa.Uuid(), nullable=True),
        sa.Column("worn_on", sa.Date(), nullable=True),
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
            ["occasion_id"], ["occasions.id"], name=op.f("fk_suggestions_occasion_id_occasions")
        ),
        sa.ForeignKeyConstraint(
            ["saved_outfit_id"],
            ["outfits.id"],
            name=op.f("fk_suggestions_saved_outfit_id_outfits"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["outfit_templates.id"],
            name=op.f("fk_suggestions_template_id_outfit_templates"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_suggestions_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["wear_log_id"],
            ["wear_logs.id"],
            name=op.f("fk_suggestions_wear_log_id_wear_logs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suggestions")),
    )
    op.create_index(
        "ix_suggestions_user_id_created_at", "suggestions", ["user_id", "created_at"], unique=False
    )
    op.create_table(
        "suggestion_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("suggestion_id", sa.Uuid(), nullable=True),
        sa.Column("item_ids", postgresql.ARRAY(sa.Uuid()), nullable=False),
        sa.Column("occasion_id", sa.String(), nullable=True),
        sa.Column("verdict", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("item_id", sa.Uuid(), nullable=True),
        sa.Column("engine_version", sa.String(), nullable=False),
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
            name=op.f("fk_suggestion_feedback_item_id_items"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["occasion_id"],
            ["occasions.id"],
            name=op.f("fk_suggestion_feedback_occasion_id_occasions"),
        ),
        sa.ForeignKeyConstraint(
            ["suggestion_id"],
            ["suggestions.id"],
            name=op.f("fk_suggestion_feedback_suggestion_id_suggestions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_suggestion_feedback_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suggestion_feedback")),
    )
    op.create_index(
        op.f("ix_suggestion_feedback_suggestion_id"),
        "suggestion_feedback",
        ["suggestion_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_suggestion_feedback_user_id"), "suggestion_feedback", ["user_id"], unique=False
    )
    op.add_column(
        "outfits", sa.Column("source", sa.String(), server_default="manual", nullable=False)
    )
    op.add_column("outfits", sa.Column("engine_version", sa.String(), nullable=True))
    op.add_column("outfits", sa.Column("score", sa.Double(), nullable=True))
    op.add_column(
        "outfits",
        sa.Column(
            "reasons", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("outfits", "reasons")
    op.drop_column("outfits", "score")
    op.drop_column("outfits", "engine_version")
    op.drop_column("outfits", "source")
    op.drop_index(op.f("ix_suggestion_feedback_user_id"), table_name="suggestion_feedback")
    op.drop_index(op.f("ix_suggestion_feedback_suggestion_id"), table_name="suggestion_feedback")
    op.drop_table("suggestion_feedback")
    op.drop_index("ix_suggestions_user_id_created_at", table_name="suggestions")
    op.drop_table("suggestions")
