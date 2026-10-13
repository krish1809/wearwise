"""Photo uploads: check the file, clean it, resize it, store it, and suggest a colour."""

import io
import uuid
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.storage import Storage
from app.engine.color import dominant_color, hex_to_rgb, nearest_family, rgb_to_hex
from app.models import ColorFamily, ItemImage, User

# The formats phones and cameras save, decided by the file's content, not its name.
ALLOWED_FORMATS = {"JPEG": "JPEG", "PNG": "PNG", "WEBP": "WebP", "MPO": "JPEG"}
# Refuses "decompression bombs": small files that expand to enormous images.
MAX_PIXELS = 50_000_000
MB = 1024 * 1024
FULL_SIZE = 1600
THUMB_SIZE = 400
# Photos uploaded but never saved with an item are removed after this long.
UNATTACHED_FOR = timedelta(days=1)


class PhotoRejected(Exception):
    """The upload isn't a photo we can use. The message says why, for the person."""


@dataclass(frozen=True)
class ProcessedPhoto:
    full: bytes
    thumb: bytes
    width: int
    height: int
    dominant_hex: str


def too_large(size: int, max_mb: int) -> str | None:
    """The message for a file over the limit, or None if it fits."""
    if size <= max_mb * MB:
        return None
    return f"That file is {size / MB:.1f} MB. Photos can be up to {max_mb} MB."


def process(data: bytes, max_mb: int) -> ProcessedPhoto:
    """Check and convert an upload: upright, no metadata, WebP at two sizes."""
    message = too_large(len(data), max_mb)
    if message:
        raise PhotoRejected(message)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            opened = Image.open(io.BytesIO(data))
            if opened.format not in ALLOWED_FORMATS:
                raise PhotoRejected(_NOT_A_PHOTO)
            if opened.width * opened.height > MAX_PIXELS:
                raise PhotoRejected(_TOO_MANY_PIXELS)
            opened.load()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        raise PhotoRejected(_NOT_A_PHOTO) from error
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise PhotoRejected(_TOO_MANY_PIXELS) from error

    # Phones store rotation as a tag; apply it, since the tag is dropped below.
    image = _flatten(ImageOps.exif_transpose(opened))

    full = image.copy()
    full.thumbnail((FULL_SIZE, FULL_SIZE), Image.Resampling.LANCZOS)
    thumb = image.copy()
    thumb.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.Resampling.LANCZOS)
    sample = image.copy()
    sample.thumbnail((64, 64), Image.Resampling.BILINEAR)

    return ProcessedPhoto(
        # Saving without exif= leaves out every tag, including the location.
        full=_webp(full, quality=82),
        thumb=_webp(thumb, quality=78),
        width=full.width,
        height=full.height,
        dominant_hex=rgb_to_hex(dominant_color(list(_rgb_pixels(sample)), *sample.size)),
    )


_NOT_A_PHOTO = "That file isn't a photo WearWise can read. Use a JPEG, PNG, or WebP image."
_TOO_MANY_PIXELS = "That photo has too many pixels to process. Use one under 50 megapixels."


def _flatten(image: Image.Image) -> Image.Image:
    """RGB, with any transparency laid on white."""
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def _webp(image: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=quality, method=4)
    return buffer.getvalue()


def _rgb_pixels(image: Image.Image) -> list[tuple[int, int, int]]:
    data = image.tobytes()
    return [(data[i], data[i + 1], data[i + 2]) for i in range(0, len(data), 3)]


def suggest_family(db: Session, dominant_hex: str) -> str | None:
    """The colour family closest to the photo's main colour."""
    families = [(id_, hex_) for id_, hex_ in db.execute(select(ColorFamily.id, ColorFamily.hex))]
    usable = [(id_, hex_) for id_, hex_ in families if hex_]
    return nearest_family(hex_to_rgb(dominant_hex), usable) if usable else None


def save_upload(db: Session, storage: Storage, user: User, photo: ProcessedPhoto) -> ItemImage:
    """Store both sizes, then record them. The files are written before the database row, so a
    failed write leaves no row pointing at nothing."""
    image_id = uuid.uuid7()
    prefix = f"users/{user.id}/{image_id}"
    storage.put(f"{prefix}/full.webp", photo.full, "image/webp")
    storage.put(f"{prefix}/thumb.webp", photo.thumb, "image/webp")
    image = ItemImage(
        id=image_id,
        user_id=user.id,
        storage_key=f"{prefix}/full.webp",
        thumb_key=f"{prefix}/thumb.webp",
        width=photo.width,
        height=photo.height,
        dominant_hex=photo.dominant_hex,
    )
    db.add(image)
    db.flush()
    return image


def find_photo(db: Session, user: User, image_id: uuid.UUID) -> ItemImage | None:
    query = select(ItemImage).where(ItemImage.id == image_id, ItemImage.user_id == user.id)
    return db.scalar(query)


def remove_unattached(db: Session, user: User) -> list[str]:
    """Delete this person's photos that were uploaded but never saved with an item. Returns the
    storage keys, to delete once the change is committed."""
    cutoff = datetime.now(UTC) - UNATTACHED_FOR
    stale = list(
        db.scalars(
            select(ItemImage).where(
                ItemImage.user_id == user.id,
                ItemImage.item_id.is_(None),
                ItemImage.created_at < cutoff,
            )
        )
    )
    keys = [key for image in stale for key in (image.storage_key, image.thumb_key)]
    for image in stale:
        db.delete(image)
    db.flush()
    return keys
