"""The name an item is shown by: its own, or its colour and category ("Navy t-shirt")."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ColorFamily, Item, User
from app.services import categories


class ItemNames:
    """Category and colour names, looked up once, for naming many items."""

    def __init__(self, db: Session, user: User) -> None:
        self.categories = {c.id: c.name for c in categories.list_categories(db, user)}
        self.colors = {
            id_: name for id_, name in db.execute(select(ColorFamily.id, ColorFamily.name))
        }

    def display_name(self, item: Item) -> str:
        if item.name:
            return item.name
        colour = _short(self.colors.get(item.color_primary, ""))
        category = _short(self.categories.get(item.category_id, "item"))
        name = f"{colour} {category[:1].lower()}{category[1:]}".strip()
        return name[:1].upper() + name[1:]


def _short(name: str) -> str:
    # "Cream / off-white" -> "Cream"; "Gold (metal)" -> "Gold".
    return name.split(" / ")[0].split(" (")[0]
