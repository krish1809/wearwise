"""add weather, events, the week plan, trips, and category traits

Revision ID: 06a4fcacacc1
Revises: 9f8e8bba4f36
Create Date: 2026-10-20 10:55:15.187257
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "06a4fcacacc1"
down_revision: str | Sequence[str] | None = "9f8e8bba4f36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "weather_forecasts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("latitude", sa.Double(), nullable=False),
        sa.Column("longitude", sa.Double(), nullable=False),
        sa.Column("fetched_on", sa.Date(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("days", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_weather_forecasts")),
    )
    op.create_index(
        "uq_weather_forecasts_place_day",
        "weather_forecasts",
        ["latitude", "longitude", "fetched_on"],
        unique=True,
    )
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("occasion_id", sa.String(), nullable=False),
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
            ["occasion_id"], ["occasions.id"], name=op.f("fk_events_occasion_id_occasions")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_events_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_events")),
    )
    op.create_index("ix_events_user_id_day", "events", ["user_id", "day"], unique=False)
    op.create_table(
        "trips",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("destination", sa.String(), nullable=False),
        sa.Column("latitude", sa.Double(), nullable=True),
        sa.Column("longitude", sa.Double(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("days", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "outfits", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column("engine_version", sa.String(), nullable=True),
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
            ["user_id"], ["users.id"], name=op.f("fk_trips_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trips")),
    )
    op.create_index(op.f("ix_trips_user_id"), "trips", ["user_id"], unique=False)
    op.create_table(
        "plan_days",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("occasion_id", sa.String(), nullable=True),
        sa.Column("planned_occasion_id", sa.String(), nullable=True),
        sa.Column("template_id", sa.String(), nullable=True),
        sa.Column("item_ids", postgresql.ARRAY(sa.Uuid()), server_default="{}", nullable=False),
        sa.Column("core_ids", postgresql.ARRAY(sa.Uuid()), server_default="{}", nullable=False),
        sa.Column("score", sa.Double(), nullable=True),
        sa.Column(
            "reasons", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column(
            "missing", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column("locked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("wear_log_id", sa.Uuid(), nullable=True),
        sa.Column(
            "weather", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("engine_version", sa.String(), nullable=True),
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
            ["occasion_id"], ["occasions.id"], name=op.f("fk_plan_days_occasion_id_occasions")
        ),
        sa.ForeignKeyConstraint(
            ["planned_occasion_id"],
            ["occasions.id"],
            name=op.f("fk_plan_days_planned_occasion_id_occasions"),
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["outfit_templates.id"],
            name=op.f("fk_plan_days_template_id_outfit_templates"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_plan_days_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["wear_log_id"],
            ["wear_logs.id"],
            name=op.f("fk_plan_days_wear_log_id_wear_logs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_days")),
    )
    op.create_index("uq_plan_days_user_id_day", "plan_days", ["user_id", "day"], unique=True)
    op.create_table(
        "trip_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trip_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
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
            ["item_id"], ["items.id"], name=op.f("fk_trip_items_item_id_items"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["trip_id"], ["trips.id"], name=op.f("fk_trip_items_trip_id_trips"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trip_items")),
    )
    op.create_index(op.f("ix_trip_items_item_id"), "trip_items", ["item_id"], unique=False)
    op.create_index(
        "uq_trip_items_trip_id_item_id", "trip_items", ["trip_id", "item_id"], unique=True
    )
    op.add_column(
        "categories",
        sa.Column("traits", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
    )
    op.add_column("profiles", sa.Column("latitude", sa.Double(), nullable=True))
    op.add_column("profiles", sa.Column("longitude", sa.Double(), nullable=True))
    op.add_column("profiles", sa.Column("manual_weather", sa.String(), nullable=True))
    op.add_column(
        "profiles",
        sa.Column(
            "weekday_occasions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )
    op.add_column("profiles", sa.Column("laundry_weekday", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "laundry_weekday")
    op.drop_column("profiles", "weekday_occasions")
    op.drop_column("profiles", "manual_weather")
    op.drop_column("profiles", "longitude")
    op.drop_column("profiles", "latitude")
    op.drop_column("categories", "traits")
    op.drop_index("uq_trip_items_trip_id_item_id", table_name="trip_items")
    op.drop_index(op.f("ix_trip_items_item_id"), table_name="trip_items")
    op.drop_table("trip_items")
    op.drop_index("uq_plan_days_user_id_day", table_name="plan_days")
    op.drop_table("plan_days")
    op.drop_index(op.f("ix_trips_user_id"), table_name="trips")
    op.drop_table("trips")
    op.drop_index("ix_events_user_id_day", table_name="events")
    op.drop_table("events")
    op.drop_index("uq_weather_forecasts_place_day", table_name="weather_forecasts")
    op.drop_table("weather_forecasts")
