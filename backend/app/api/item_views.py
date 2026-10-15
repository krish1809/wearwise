"""How items appear inside other things: in matching sets, outfits, and the wear log."""

import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Item, ItemImage, VocabularyTerm
from app.services.item_names import ItemNames


class PhotoRef(BaseModel):
    id: uuid.UUID
    url: str
    thumb_url: str
    width: int
    height: int


class ItemBrief(BaseModel):
    id: uuid.UUID
    display_name: str
    category_id: str
    slot: str
    color_primary: str
    color_hex: str | None
    status: str
    archived: bool
    photo: PhotoRef | None


def photo_ref(image: ItemImage | None) -> PhotoRef | None:
    if image is None:
        return None
    return PhotoRef(
        id=image.id,
        url=f"/api/v1/photos/{image.id}/full",
        thumb_url=f"/api/v1/photos/{image.id}/thumb",
        width=image.width,
        height=image.height,
    )


class Names(ItemNames):
    """Display names, plus the brief form other responses embed."""

    def brief(self, item: Item, photo: ItemImage | None) -> ItemBrief:
        return ItemBrief(
            id=item.id,
            display_name=self.display_name(item),
            category_id=item.category_id,
            slot=item.slot,
            color_primary=item.color_primary,
            color_hex=item.color_hex,
            status=item.status,
            archived=item.archived_at is not None,
            photo=photo_ref(photo),
        )


def briefs(db: Session, names: Names, item_ids: list[uuid.UUID]) -> dict[uuid.UUID, ItemBrief]:
    """Brief forms of the given items (which the caller has already scoped to one person)."""
    ids = list({item_id for item_id in item_ids})
    if not ids:
        return {}
    found = list(db.scalars(select(Item).where(Item.id.in_(ids))))
    photos = {
        image.item_id: image
        for image in db.scalars(
            select(ItemImage).where(ItemImage.item_id.in_(ids), ItemImage.is_primary)
        )
        if image.item_id
    }
    return {item.id: names.brief(item, photos.get(item.id)) for item in found}


def slot_order(db: Session) -> dict[str, int]:
    """Slots in the seed's order (top, bottom, one-piece, layer, footwear, accessories...)."""
    query = select(VocabularyTerm.id, VocabularyTerm.position).where(VocabularyTerm.kind == "slot")
    return {slot: position for slot, position in db.execute(query)}
