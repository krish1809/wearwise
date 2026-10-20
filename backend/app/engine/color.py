"""Colour from a photo, and the nearest colour family. Plain data in, plain data out.

The dominant colour is the one that fills the middle of the photo but not its edges: clothes
are usually photographed in the middle, on a bed, a floor, or a wall that fills the border.
Families are matched by distance in CIELAB, a colour space where equal distances look about
equally different to people, unlike RGB.
"""

import math
from collections import defaultdict
from collections.abc import Sequence
from functools import lru_cache

RGB = tuple[int, int, int]

# 8 levels per channel: coarse enough that one garment's shades share a bucket.
_LEVELS = 8
_STEP = 256 // _LEVELS
# Distance in CIELAB under which two colours read as shades of one colour.
_SAME_COLOUR = 10.0


def hex_to_rgb(value: str) -> RGB:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def rgb_to_hex(rgb: RGB) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def dominant_color(pixels: Sequence[RGB], width: int, height: int) -> RGB:
    """The main colour of the thing in the middle of the photo.

    `pixels` is row by row, `width * height` of them. Each pixel goes into a coarse colour
    bucket. A bucket scores by how much of the middle it covers minus how much of the border
    it covers, so the background loses. If nothing stands out (a close-up that fills the whole
    photo), the bucket covering most of the middle wins.
    """
    if not pixels or len(pixels) != width * height:
        raise ValueError("pixels must hold width * height values")
    middle: dict[RGB, list[RGB]] = defaultdict(list)
    border: dict[RGB, int] = defaultdict(int)
    border_total = 0
    for index, pixel in enumerate(pixels):
        x, y = index % width, index // width
        bucket = (pixel[0] // _STEP, pixel[1] // _STEP, pixel[2] // _STEP)
        if width * 0.25 <= x < width * 0.75 and height * 0.25 <= y < height * 0.75:
            middle[bucket].append(pixel)
        elif x < width * 0.1 or x >= width * 0.9 or y < height * 0.1 or y >= height * 0.9:
            border[bucket] += 1
            border_total += 1
    if not middle:
        middle = defaultdict(list)
        for pixel in pixels:
            middle[(pixel[0] // _STEP, pixel[1] // _STEP, pixel[2] // _STEP)].append(pixel)
    middle_total = sum(len(group) for group in middle.values())

    def score(bucket: RGB) -> float:
        share = len(middle[bucket]) / middle_total
        background = border[bucket] / border_total if border_total else 0.0
        return share - background

    best = max(middle, key=score)
    if score(best) <= 0:
        best = max(middle, key=lambda bucket: len(middle[bucket]))
    centre = _to_lab(_mean(middle[best]))
    # One garment's shades can straddle a bucket edge; gather every middle pixel that looks
    # like the winner, whichever bucket it fell into.
    alike = [
        pixel
        for group in middle.values()
        for pixel in group
        if math.dist(_to_lab(pixel), centre) <= _SAME_COLOUR
    ]
    return _mean(alike or middle[best])


def _mean(pixels: Sequence[RGB]) -> RGB:
    count = len(pixels)
    return (
        round(sum(p[0] for p in pixels) / count),
        round(sum(p[1] for p in pixels) / count),
        round(sum(p[2] for p in pixels) / count),
    )


def _to_lab(rgb: RGB) -> tuple[float, float, float]:
    r, g, b = (_linear(c) for c in rgb)
    # sRGB to XYZ (D65), scaled to the reference white.
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def nearest_family(rgb: RGB, families: Sequence[tuple[str, str]]) -> str:
    """The id of the family whose representative colour looks closest. `families` holds
    (id, hex) pairs; families without a hex (multicolour) can't be matched and are left out."""
    if not families:
        raise ValueError("no colour families to match against")
    target = _to_lab(rgb)
    return min(families, key=lambda family: math.dist(target, _to_lab(hex_to_rgb(family[1]))))[0]


@lru_cache(maxsize=4096)
def oklch(hex_value: str) -> tuple[float, float, float]:
    """Lightness (0 to 1), chroma (0 to about 0.37), and hue (degrees) in OKLCH.

    OKLCH is built so that equal steps in hue and lightness look about equally large, which is
    what the engine's colour rules are written in (docs/ENGINE.md, section 5).
    """
    r, g, b = (_linear(channel) for channel in hex_to_rgb(hex_value))
    l_ = math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m_ = math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s_ = math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    lightness = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b_ = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    chroma = math.hypot(a, b_)
    hue = math.degrees(math.atan2(b_, a)) % 360
    return (lightness, chroma, hue)


def hue_distance(first: float, second: float) -> float:
    """Degrees between two hues the short way round the circle, 0 to 180."""
    gap = abs(first - second) % 360
    return min(gap, 360 - gap)


def _linear(channel: int) -> float:
    c = channel / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
