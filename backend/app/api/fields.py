"""Reusable request fields whose error messages read well next to a form input."""

import re
from collections.abc import Callable
from typing import Annotated, Any

from pydantic import AfterValidator, BeforeValidator

# Money is in minor units (paise). A crore a month is far beyond any real budget.
MAX_MONEY = 1_000_000_000
MAX_MONEY_TEXT = "₹1,00,00,000"


def tidy_text(max_length: int) -> Callable[[str | None], str | None]:
    """Trim the text; blank becomes null."""

    def tidy(value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) > max_length:
            raise ValueError(f"Keep this to {max_length} characters or fewer.")
        return value or None

    return tidy


def required_text(max_length: int, empty_message: str) -> Callable[[str], str]:
    """Trim the text; blank is an error."""

    def check(value: str) -> str:
        tidied = tidy_text(max_length)(value)
        if tidied is None:
            raise ValueError(empty_message)
        return tidied

    return check


def centimetres(low: int, high: int) -> Callable[[float | None], float | None]:
    """A body measurement in cm, kept to one decimal place."""

    def check(value: float | None) -> float | None:
        if value is None:
            return None
        if not low <= value <= high:
            raise ValueError(f"Enter a number between {low} and {high} cm.")
        return round(value, 1)

    return check


def _check_amount(value: int) -> int:
    if not 0 <= value <= MAX_MONEY:
        raise ValueError(f"Enter an amount in rupees, up to {MAX_MONEY_TEXT}.")
    return value


def _check_hex(value: str | None) -> str | None:
    if value is not None and not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        raise ValueError("Use a colour code like #1F2A44.")
    return value.upper() if value else None


def _unique(values: Any) -> Any:
    # Repeats are dropped, first one kept, so a double tap can't store a value twice.
    if isinstance(values, list):
        return list(dict.fromkeys(values))
    return values


ShortText = Annotated[str | None, AfterValidator(tidy_text(100))]
NoteText = Annotated[str | None, AfterValidator(tidy_text(500))]
# Money in minor units (paise).
Amount = Annotated[int, AfterValidator(_check_amount)]
IdList = Annotated[list[str] | None, BeforeValidator(_unique)]
# A colour code such as #1F2A44, kept in capitals.
HexColour = Annotated[str | None, AfterValidator(_check_hex)]
