from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class AppMeta(IdMixin, TimestampMixin, Base):
    """Facts about the database itself, as key-value rows."""

    __tablename__ = "app_meta"

    key: Mapped[str] = mapped_column(unique=True)
    value: Mapped[str]
