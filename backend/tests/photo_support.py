"""Test photos, made on the fly."""

import io

from PIL import Image

NAVY = (31, 42, 68)


def photo_bytes(
    size: tuple[int, int] = (300, 400),
    garment: tuple[int, int, int] = NAVY,
    fmt: str = "PNG",
    exif: Image.Exif | None = None,
) -> bytes:
    """A garment-coloured rectangle on a pale background, like a shirt laid on a bed."""
    image = Image.new("RGB", size, (236, 234, 230))
    width, height = size
    image.paste(garment, (width // 4, height // 4, width * 3 // 4, height * 3 // 4))
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **({"exif": exif} if exif is not None else {}))
    return buffer.getvalue()
