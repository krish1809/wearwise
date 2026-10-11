"""SQLAlchemy tables. Import every model here so Alembic's autogenerate can see it."""

from app.models.app_meta import AppMeta
from app.models.base import Base

__all__ = ["AppMeta", "Base"]
