"""The fixed lists the app offers: sections, fits, sizing systems, colours, occasions, styles."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, model_validator

from app.api.deps import CurrentUser, SessionDep
from app.api.errors import error_responses
from app.models import CategoryGroup, ColorFamily, Occasion, StyleProfile
from app.services import reference

router = APIRouter(tags=["reference"])


class Term(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str


class ColorFamilyOut(Term):
    # Empty for multicolour.
    hex: str | None
    neutrality: float


class OccasionOut(Term):
    formality_min: int
    formality_max: int
    hint: str | None


class StyleProfileOut(Term):
    description: str
    # Colour family ids that signal the style, for the swatches on its card.
    palette: list[str]

    @model_validator(mode="before")
    @classmethod
    def palette_from_signals(cls, data: Any) -> Any:
        if isinstance(data, StyleProfile):
            return {
                "id": data.id,
                "name": data.name,
                "description": data.description,
                "palette": list(data.signals.get("colors", [])),
            }
        return data


class ReferenceOut(BaseModel):
    sections: list[Term]
    fits: list[Term]
    sizing_systems: list[Term]
    slots: list[Term]
    patterns: list[Term]
    fabrics: list[Term]
    seasons: list[Term]
    statuses: list[Term]
    # "1" (lounge or sport) to "5" (formal or ceremonial).
    formality_levels: list[Term]
    category_groups: list[Term]
    color_families: list[ColorFamilyOut]
    occasions: list[OccasionOut]
    style_profiles: list[StyleProfileOut]


@router.get("/reference", response_model=ReferenceOut, responses=error_responses(401))
def get_reference(_: CurrentUser, db: SessionDep) -> ReferenceOut:
    """Every list in one response: they're small, change only on deploy, and load once per visit."""

    def terms(kind: str) -> list[Term]:
        return [Term.model_validate(t) for t in reference.terms(db, kind)]

    return ReferenceOut(
        sections=terms("section"),
        fits=terms("fit"),
        sizing_systems=terms("sizing_system"),
        slots=terms("slot"),
        patterns=terms("pattern"),
        fabrics=terms("fabric"),
        seasons=terms("season"),
        statuses=terms("status"),
        formality_levels=terms("formality"),
        category_groups=[Term.model_validate(g) for g in reference.ordered(db, CategoryGroup)],
        color_families=[
            ColorFamilyOut.model_validate(c) for c in reference.ordered(db, ColorFamily)
        ],
        occasions=[OccasionOut.model_validate(o) for o in reference.ordered(db, Occasion)],
        style_profiles=[
            StyleProfileOut.model_validate(s) for s in reference.ordered(db, StyleProfile)
        ],
    )
