from app.engine.color import dominant_color, hex_to_rgb, nearest_family, rgb_to_hex

NAVY = (31, 42, 68)
WHITE = (250, 250, 250)
FAMILIES = [
    ("black", "#111111"),
    ("white", "#FFFFFF"),
    ("navy", "#1F2A44"),
    ("red", "#C0282D"),
    ("olive", "#6B6B3A"),
]


def picture(
    width: int,
    height: int,
    background: tuple[int, int, int],
    garment: tuple[int, int, int],
    inset: float,
) -> list[tuple[int, int, int]]:
    """A garment-coloured rectangle on a background, row by row."""
    pixels = []
    for y in range(height):
        for x in range(width):
            inside = (
                inset * width <= x < (1 - inset) * width
                and inset * height <= y < (1 - inset) * height
            )
            pixels.append(garment if inside else background)
    return pixels


def test_the_garment_wins_over_a_background_that_covers_more_of_the_photo() -> None:
    # The navy shirt covers only the middle third; the white bed covers the rest.
    pixels = picture(60, 60, WHITE, NAVY, inset=0.33)

    assert dominant_color(pixels, 60, 60) == NAVY


def test_a_close_up_that_fills_the_photo_still_gets_its_colour() -> None:
    pixels = picture(40, 40, NAVY, NAVY, inset=0.2)

    assert dominant_color(pixels, 40, 40) == NAVY


def test_slightly_different_shades_of_one_garment_are_averaged() -> None:
    shades = [(30, 40, 66), (33, 44, 70)]
    pixels = [
        WHITE if (x < 10 or x >= 30 or y < 10 or y >= 30) else shades[(x + y) % 2]
        for y in range(40)
        for x in range(40)
    ]

    assert dominant_color(pixels, 40, 40) == (32, 42, 68)


def test_colours_map_to_the_family_that_looks_closest() -> None:
    assert nearest_family((40, 50, 80), FAMILIES) == "navy"
    assert nearest_family((180, 30, 40), FAMILIES) == "red"
    assert nearest_family((245, 245, 240), FAMILIES) == "white"
    assert nearest_family((100, 100, 60), FAMILIES) == "olive"


def test_hex_round_trips() -> None:
    assert rgb_to_hex(hex_to_rgb("#1f2a44")) == "#1F2A44"
