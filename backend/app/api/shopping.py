"""Shopping: candidates and what each would add, gaps, the starter capsule, the budget split,
and the Style Guide."""

import uuid
from datetime import date, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query, status
from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep, StorageDep
from app.api.errors import ApiError, error_responses
from app.api.fields import Amount, HexColour, IdList, NoteText, ShortText, tidy_text
from app.api.item_views import ItemBrief, Names, PhotoRef, photo_ref
from app.engine.config import DEFAULT
from app.models import Archetype, Candidate, Item, User
from app.services import items, rate_limit, shopping, wear

router = APIRouter(tags=["shopping"])

SHOPPING_PER_USER = rate_limit.Limit(attempts=300, window=timedelta(hours=1))
GAPS_SHOWN = 8
CAPSULE_STAGE = 3
MAX_COMPARE = 4
NEEDS_OCCASIONS = (
    "Choose the occasions you dress for (in Settings, or your usual week in My Week) so "
    "WearWise can tell what a piece would add."
)


def _check_url(value: str | None) -> str | None:
    value = tidy_text(500)(value)
    if value is not None and not value.lower().startswith(("https://", "http://")):
        raise ValueError("Paste a link that starts with https://.")
    return value


Url = Annotated[str | None, AfterValidator(_check_url)]


class CandidateFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ShortText = None
    brand: ShortText = None
    url: Url = None
    size_label: Annotated[str | None, AfterValidator(tidy_text(20))] = None
    color_secondary: str | None = None
    color_hex: HexColour = None
    pattern: str | None = None
    fabric: str | None = None
    fit: str | None = None
    formality: int | None = Field(default=None, ge=1, le=5)
    warmth: int | None = Field(default=None, ge=0, le=5)
    seasons: IdList = None
    # Minor units (paise); the time it was given is kept with it.
    price: Amount | None = None
    target_price: Amount | None = None
    status: str | None = None
    notes: NoteText = None
    # A photo from POST /photos that isn't attached to anything yet.
    photo_id: uuid.UUID | None = None


class CandidateCreate(CandidateFields):
    category_id: str
    color_primary: str


class CandidateUpdate(CandidateFields):
    """Only the fields sent are changed; null clears an optional one, and photo_id null
    removes the photo."""

    category_id: str | None = None
    color_primary: str | None = None


class FromStaple(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archetype_id: str


class CandidateOut(BaseModel):
    id: uuid.UUID
    source: str
    archetype_id: str | None
    name: str | None
    display_name: str
    brand: str | None
    url: str | None
    size_label: str | None
    price: int | None
    currency: str
    # When the price was given; a price is never shown without it.
    price_checked_at: datetime | None
    target_price: int | None
    category_id: str
    slot: str
    color_primary: str
    color_secondary: str | None
    color_hex: str | None
    pattern: str
    fabric: str | None
    fit: str | None
    formality: int
    warmth: int
    seasons: list[str]
    status: str
    notes: str | None
    # The wardrobe item it became, once bought.
    item_id: uuid.UUID | None
    photo: PhotoRef | None
    # Buy, consider, or skip, when an up-to-date analysis is stored; null until worked out.
    verdict: str | None
    created_at: datetime
    updated_at: datetime


class CandidateList(BaseModel):
    candidates: list[CandidateOut]
    needs_occasions: bool


class VerdictReasonOut(BaseModel):
    code: str
    kind: Literal["positive", "caution"]
    text: str


class CoverageCellOut(BaseModel):
    occasion_id: str
    season: str
    # Good outfits now, and how many more the candidate would make.
    before: int
    added: int


class MatchOut(BaseModel):
    item: ItemBrief
    score: float


class PieceOut(BaseModel):
    # An owned piece, or null for the candidate itself.
    item: ItemBrief | None
    candidate: bool


class ExampleOut(BaseModel):
    template_id: str
    pieces: list[PieceOut]


class ProjectedOut(BaseModel):
    """An estimate, always shown as one: the price over the wears a year the person's other
    pieces of the same category get."""

    wears_a_year: int
    per_wear: int
    similar: int


class AnalysisOut(BaseModel):
    kind: str
    verdict: str
    reasons: list[VerdictReasonOut]
    # Distinct good outfits it makes (clothes) or finishes (accessories).
    new_outfits: int
    coverage_gain: float
    cells: list[CoverageCellOut]
    matches: list[MatchOut]
    closest: ItemBrief | None
    redundancy: float
    rescued: list[ItemBrief]
    examples: list[ExampleOut]
    cost_per_new_outfit: int | None
    projected: ProjectedOut | None
    # The person's usual spend for its kind of clothing, and whether the price is within it.
    usual_spend: int | None
    within_budget: bool | None
    engine_version: str


class CandidateAnalysed(BaseModel):
    candidate: CandidateOut
    analysis: AnalysisOut


class CompareOut(BaseModel):
    candidates: list[CandidateAnalysed]


class Purchase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # What was paid, if different from the price noted.
    price: Amount | None = None
    purchased_on: date | None = None
    size_label: Annotated[str | None, AfterValidator(tidy_text(20))] = None


class PurchaseOut(BaseModel):
    item_id: uuid.UUID


class StapleOut(BaseModel):
    id: str
    name: str
    category_id: str
    slot: str
    color: str
    hex: str | None
    pattern: str
    fabric: str | None
    group_id: str
    # The person's usual spend for its group, if set.
    usual_spend: int | None
    # Already on the shopping list (and not skipped or bought).
    on_list: bool


class GapCellOut(BaseModel):
    occasion_id: str
    season: str
    added: int


class GapOut(BaseModel):
    # One staple, or several that together make a first good outfit.
    staples: list[StapleOut]
    coverage_gain: float
    new_outfits: int
    cells: list[GapCellOut]
    reason: str


class GapsOut(BaseModel):
    needs_occasions: bool
    gaps: list[GapOut]
    # True when every occasion and season already has plenty of good outfits.
    covered: bool


class CapsuleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Null plans by count alone.
    budget: Amount | None = None


class CapsuleStepOut(BaseModel):
    staples: list[StapleOut]
    coverage_gain: float
    cost: int | None
    # 1 for the first purchases, 2 for the next, and so on.
    stage: int


class GroupOut(BaseModel):
    id: str
    name: str


class CapsuleOut(BaseModel):
    steps: list[CapsuleStepOut]
    budget: int | None
    total: int | None
    unpriced_groups: list[GroupOut]


class SplitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    budget: Amount


class SplitOut(BaseModel):
    budget: int
    chosen: list[CandidateOut]
    # Priced and weighed, but not in the best set.
    left: list[CandidateOut]
    # No price, so not weighed.
    unpriced: list[CandidateOut]
    coverage_gain: float
    spent: int
    # True when every affordable combination was compared.
    exhaustive: bool


class FabricOut(BaseModel):
    id: str
    name: str
    feel: str
    seasons: list[str]
    care: str
    label: str
    watch: str


class ColourBasicOut(BaseModel):
    id: str
    title: str
    text: str


class FamilyOut(BaseModel):
    id: str
    name: str
    hex: str | None


class StylePieceOut(BaseModel):
    staple: StapleOut
    owned: ItemBrief | None


class GuideStyleOut(BaseModel):
    id: str
    name: str
    description: str
    colors: list[FamilyOut]
    fabrics: list[str]
    pieces: list[StylePieceOut]
    chosen: bool


class GuideOut(BaseModel):
    fabrics: list[FabricOut]
    colour: list[ColourBasicOut]
    neutrals: list[FamilyOut]
    styles: list[GuideStyleOut]


# Helpers.


def _owned(db: Session, user: User, candidate_id: uuid.UUID) -> Candidate:
    candidate = shopping.find(db, user, candidate_id)
    if candidate is None:
        raise ApiError(404, "candidate_not_found", "That isn't on your shopping list.")
    return candidate


def _invalid(error: shopping.CandidateInvalid) -> ApiError:
    return ApiError(422, "invalid_input", "Check the highlighted fields.", fields=error.fields)


def _limited(db: Session, user: User) -> None:
    try:
        rate_limit.hit(db, f"shopping:user:{user.id}", SHOPPING_PER_USER)
    except rate_limit.RateLimited as error:
        db.commit()
        raise ApiError(
            429, "rate_limited", "That's a lot of analysis in an hour. Try again a little later."
        ) from error


def _needs_occasions() -> ApiError:
    return ApiError(409, "needs_occasions", NEEDS_OCCASIONS)


_COLUMNS = [
    name for name in CandidateOut.model_fields if name not in {"display_name", "photo", "verdict"}
]


def _outs(
    db: Session, user: User, rows: list[Candidate], s: shopping.Setting | None = None
) -> list[CandidateOut]:
    names = Names(db, user)
    photos = shopping.primary_photos(db, [row.id for row in rows])
    bought = items.primary_photos(db, [row.item_id for row in rows if row.item_id])
    return [
        CandidateOut.model_validate(
            {
                **{name: getattr(row, name) for name in _COLUMNS},
                "display_name": names.display_name(row),
                "photo": photo_ref(
                    photos.get(row.id) or (bought.get(row.item_id) if row.item_id else None)
                ),
                "verdict": shopping.fresh_verdict(row, s) if s else None,
            }
        )
        for row in rows
    ]


def _analysis_out(db: Session, user: User, found: dict[str, Any]) -> AnalysisOut:
    ids = {
        *(m["item_id"] for m in found["matches"]),
        *found["rescued"],
        *([found["closest_id"]] if found["closest_id"] else []),
        *(i for example in found["examples"] for i in example["item_ids"]),
    }
    owned = [uuid.UUID(i) for i in ids if not i.startswith(shopping.CANDIDATE)]
    rows = (
        {
            str(row.id): row
            for row in db.scalars(select(Item).where(Item.user_id == user.id, Item.id.in_(owned)))
        }
        if owned
        else {}
    )
    names = Names(db, user)
    photos = items.primary_photos(db, [row.id for row in rows.values()])
    briefs = {key: names.brief(row, photos.get(row.id)) for key, row in rows.items()}
    return AnalysisOut(
        kind=found["kind"],
        verdict=found["verdict"],
        reasons=[VerdictReasonOut(**reason) for reason in found["reasons"]],
        new_outfits=found["new_outfits"],
        coverage_gain=found["coverage_gain"],
        cells=[CoverageCellOut(**cell) for cell in found["cells"]],
        matches=[
            MatchOut(item=briefs[m["item_id"]], score=m["score"])
            for m in found["matches"]
            if m["item_id"] in briefs
        ],
        closest=briefs.get(found["closest_id"] or ""),
        redundancy=found["redundancy"],
        rescued=[briefs[i] for i in found["rescued"] if i in briefs],
        examples=[
            ExampleOut(
                template_id=example["template_id"],
                pieces=[
                    PieceOut(item=briefs.get(i), candidate=i.startswith(shopping.CANDIDATE))
                    for i in example["item_ids"]
                    if i in briefs or i.startswith(shopping.CANDIDATE)
                ],
            )
            for example in found["examples"]
        ],
        cost_per_new_outfit=found["cost_per_new_outfit"],
        projected=ProjectedOut(**found["projected"]) if found["projected"] else None,
        usual_spend=found["usual_spend"],
        within_budget=found["within_budget"],
        engine_version=found["engine_version"],
    )


def _staple_outs(
    db: Session, user: User, s: shopping.Setting, rows: list[Archetype]
) -> dict[str, StapleOut]:
    listed = {
        row.archetype_id
        for row in shopping.list_candidates(db, user)
        if row.archetype_id and row.status in shopping.STILL_WANTED
    }
    found = {}
    for row in rows:
        category = s.categories[row.category_id]
        found[row.id] = StapleOut(
            id=row.id,
            name=row.name,
            category_id=row.category_id,
            slot=category.slot,
            color=row.color,
            hex=s.families[row.color].hex,
            pattern=row.pattern,
            fabric=row.fabric,
            group_id=category.group_id,
            usual_spend=s.profile.category_budgets.get(category.group_id),
            on_list=row.id in listed,
        )
    return found


def _staple_id(engine_id: str) -> str:
    return engine_id.removeprefix(shopping.STAPLE)


# Candidates.


@router.get("/candidates", response_model=CandidateList, responses=error_responses(401))
def list_candidates(user: CurrentUser, db: SessionDep) -> CandidateList:
    """The shopping list, newest first, each with its verdict when one is up to date."""
    s = shopping.setting(db, user, wear.today())
    rows = shopping.list_candidates(db, user)
    return CandidateList(candidates=_outs(db, user, rows, s), needs_occasions=s.before is None)


@router.post(
    "/candidates",
    status_code=status.HTTP_201_CREATED,
    response_model=CandidateOut,
    responses=error_responses(401, 403, 409, 422),
)
def create_candidate(body: CandidateCreate, user: CurrentUser, db: SessionDep) -> CandidateOut:
    """Add something you're thinking of buying. A category and a colour are all it needs."""
    try:
        row = shopping.create(db, user, body.model_dump(exclude_unset=True))
    except shopping.CandidateInvalid as error:
        raise _invalid(error) from error
    except shopping.TooManyCandidates as error:
        message = f"Your shopping list can hold {shopping.MAX_CANDIDATES} things."
        raise ApiError(409, "too_many_candidates", message) from error
    db.commit()
    return _outs(db, user, [row])[0]


@router.post(
    "/candidates/from-staple",
    status_code=status.HTTP_201_CREATED,
    response_model=CandidateOut,
    responses=error_responses(401, 403, 409, 422),
)
def add_staple(body: FromStaple, user: CurrentUser, db: SessionDep) -> CandidateOut:
    """Put a staple from your gaps or starter plan on the shopping list."""
    try:
        row = shopping.from_staple(db, user, body.archetype_id)
    except shopping.CandidateInvalid as error:
        raise _invalid(error) from error
    except shopping.TooManyCandidates as error:
        message = f"Your shopping list can hold {shopping.MAX_CANDIDATES} things."
        raise ApiError(409, "too_many_candidates", message) from error
    db.commit()
    return _outs(db, user, [row])[0]


@router.get(
    "/candidates/compare", response_model=CompareOut, responses=error_responses(401, 404, 409, 422)
)
def compare(
    user: CurrentUser,
    db: SessionDep,
    id: Annotated[list[uuid.UUID], Query(min_length=2, max_length=MAX_COMPARE)],
) -> CompareOut:
    """Two to four candidates side by side, each with its analysis."""
    rows = [_owned(db, user, candidate_id) for candidate_id in dict.fromkeys(id)]
    _limited(db, user)
    s = shopping.setting(db, user, wear.today())
    if s.before is None:
        raise _needs_occasions()
    found = [shopping.analysis(db, row, s, wear.today()) for row in rows]
    db.commit()
    outs = _outs(db, user, rows, s)
    return CompareOut(
        candidates=[
            CandidateAnalysed(candidate=out, analysis=_analysis_out(db, user, result))
            for out, result in zip(outs, found, strict=True)
            if result is not None
        ]
    )


@router.get(
    "/candidates/{candidate_id}", response_model=CandidateOut, responses=error_responses(401, 404)
)
def get_candidate(candidate_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> CandidateOut:
    row = _owned(db, user, candidate_id)
    s = shopping.setting(db, user, wear.today())
    return _outs(db, user, [row], s)[0]


@router.patch(
    "/candidates/{candidate_id}",
    response_model=CandidateOut,
    responses=error_responses(401, 403, 404, 409, 422),
)
def update_candidate(
    candidate_id: uuid.UUID,
    body: CandidateUpdate,
    user: CurrentUser,
    db: SessionDep,
    storage: StorageDep,
) -> CandidateOut:
    row = _owned(db, user, candidate_id)
    changes = body.model_dump(exclude_unset=True)
    if "seasons" in changes and changes["seasons"] is None:
        changes["seasons"] = []
    try:
        removed = shopping.update(db, user, row, changes)
    except shopping.CandidateInvalid as error:
        raise _invalid(error) from error
    except shopping.NotForSale as error:
        raise ApiError(409, "already_bought", "This is already in your wardrobe.") from error
    db.commit()
    storage.delete(removed)
    return _outs(db, user, [row])[0]


@router.delete(
    "/candidates/{candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403, 404),
)
def delete_candidate(
    candidate_id: uuid.UUID, user: CurrentUser, db: SessionDep, storage: StorageDep
) -> None:
    removed = shopping.delete(db, _owned(db, user, candidate_id))
    db.commit()
    storage.delete(removed)


@router.get(
    "/candidates/{candidate_id}/analysis",
    response_model=AnalysisOut,
    responses=error_responses(401, 404, 409, 429),
)
def analyse(candidate_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> AnalysisOut:
    """What it would add: the outfits it makes, where you're short, what it duplicates, and
    the verdict with its reasons. Worked out again whenever the wardrobe or the settings
    behind it change."""
    row = _owned(db, user, candidate_id)
    _limited(db, user)
    s = shopping.setting(db, user, wear.today())
    found = shopping.analysis(db, row, s, wear.today())
    if found is None:
        db.commit()
        raise _needs_occasions()
    db.commit()
    return _analysis_out(db, user, found)


@router.post(
    "/candidates/{candidate_id}/purchase",
    status_code=status.HTTP_201_CREATED,
    response_model=PurchaseOut,
    responses=error_responses(401, 403, 404, 409, 422),
)
def purchase(
    candidate_id: uuid.UUID, body: Purchase, user: CurrentUser, db: SessionDep
) -> PurchaseOut:
    """Bought it: it becomes a wardrobe item, with its photo, and suggestions use it."""
    row = _owned(db, user, candidate_id)
    if body.purchased_on is not None and body.purchased_on > wear.today():
        raise ApiError(
            422,
            "invalid_input",
            "Check the highlighted fields.",
            fields={"purchased_on": "The purchase date can't be in the future."},
        )
    try:
        item = shopping.purchase(db, user, row, body.model_dump(exclude_unset=True))
    except shopping.NotForSale as error:
        raise ApiError(409, "already_bought", "This is already in your wardrobe.") from error
    except items.ItemInvalid as error:
        raise ApiError(
            422, "invalid_input", "Check the highlighted fields.", fields=error.fields
        ) from error
    db.commit()
    return PurchaseOut(item_id=item.id)


# Gaps, the capsule, and the budget split.


@router.get("/shopping/gaps", response_model=GapsOut, responses=error_responses(401, 429))
def get_gaps(user: CurrentUser, db: SessionDep) -> GapsOut:
    """What would add the most to your wardrobe, most first: a staple, or several that
    together make a first good outfit for an occasion you have nothing for."""
    _limited(db, user)
    s = shopping.setting(db, user, wear.today())
    if s.before is None:
        db.commit()
        return GapsOut(needs_occasions=True, gaps=[], covered=False)
    found = [gap for gap in shopping.gaps(db, s) if gap.coverage_gain > 0][:GAPS_SHOWN]
    rows = {row.id: row for row in shopping.staples(db, s.profile)}
    outs = _staple_outs(db, user, s, list(rows.values()))
    db.commit()
    short = any(n < DEFAULT.coverage_cap for n in s.before.coverage.values())
    return GapsOut(
        needs_occasions=False,
        gaps=[
            GapOut(
                staples=[outs[_staple_id(i)] for i in gap.item_ids],
                coverage_gain=gap.coverage_gain,
                new_outfits=gap.new_outfits,
                cells=[
                    GapCellOut(occasion_id=o, season=season, added=n)
                    for (o, season), n in gap.added.items()
                ],
                reason=gap.reason,
            )
            for gap in found
        ],
        covered=not short,
    )


@router.post(
    "/shopping/capsule", response_model=CapsuleOut, responses=error_responses(401, 403, 409, 429)
)
def plan_capsule(body: CapsuleRequest, user: CurrentUser, db: SessionDep) -> CapsuleOut:
    """A staged shopping plan, best first, within the budget: each step the staple that adds
    the most given the ones before it (or a whole first outfit when no single piece does)."""
    _limited(db, user)
    s = shopping.setting(db, user, wear.today())
    plan = shopping.capsule(db, s, body.budget)
    if plan is None:
        db.commit()
        raise _needs_occasions()
    outs = _staple_outs(db, user, s, list(plan.staples.values()))
    db.commit()
    steps = []
    pieces = 0
    for step in plan.steps:
        steps.append(
            CapsuleStepOut(
                staples=[outs[_staple_id(i)] for i in step.item_ids],
                coverage_gain=step.coverage_gain,
                cost=step.cost,
                stage=pieces // CAPSULE_STAGE + 1,
            )
        )
        pieces += len(step.item_ids)
    costs = [step.cost for step in plan.steps]
    return CapsuleOut(
        steps=steps,
        budget=body.budget,
        total=None if any(c is None for c in costs) else sum(c or 0 for c in costs),
        unpriced_groups=[
            GroupOut(id=group, name=s.groups[group]) for group in plan.unpriced_groups
        ],
    )


@router.post(
    "/shopping/split", response_model=SplitOut, responses=error_responses(401, 403, 409, 429)
)
def split_budget(body: SplitRequest, user: CurrentUser, db: SessionDep) -> SplitOut:
    """Which things on your list to buy for the most new outfits within a budget. They're
    weighed together, since a shirt and trousers make outfits neither makes alone."""
    _limited(db, user)
    s = shopping.setting(db, user, wear.today())
    plan = shopping.split(db, s, body.budget)
    if plan is None:
        db.commit()
        raise _needs_occasions()
    db.commit()
    chosen_ids = set(plan.split.chosen) if plan.split else set()
    chosen = [c for c in plan.considered if shopping.CANDIDATE + str(c.id) in chosen_ids]
    left = [c for c in plan.considered if shopping.CANDIDATE + str(c.id) not in chosen_ids]
    return SplitOut(
        budget=body.budget,
        chosen=_outs(db, user, chosen, s),
        left=_outs(db, user, left, s),
        unpriced=_outs(db, user, plan.unpriced, s),
        coverage_gain=plan.split.coverage_gain if plan.split else 0.0,
        spent=plan.split.spent if plan.split else 0,
        exhaustive=plan.split.exhaustive if plan.split else True,
    )


# The Style Guide.


@router.get("/guide", response_model=GuideOut, responses=error_responses(401))
def guide(user: CurrentUser, db: SessionDep) -> GuideOut:
    """Fabrics, colour basics, and each style with the staples it's built on and which of
    them you already have."""
    today = wear.today()
    s = shopping.setting(db, user, today)
    entries, neutrals = shopping.colour_guide(db)
    styles = shopping.style_guides(db, user, today)
    staples = _staple_outs(
        db, user, s, list({p.staple.id: p.staple for g in styles for p in g.pieces}.values())
    )
    owned = [p.owned for g in styles for p in g.pieces if p.owned is not None]
    names = Names(db, user)
    photos = items.primary_photos(db, [row.id for row in owned])
    fabric_names = {term.id: term.name for term, _ in shopping.fabric_guide(db)}
    return GuideOut(
        fabrics=[
            FabricOut(id=term.id, name=term.name, **entry.body)
            for term, entry in shopping.fabric_guide(db)
        ],
        colour=[ColourBasicOut(id=entry.id, **entry.body) for entry in entries],
        neutrals=[FamilyOut(id=f.id, name=f.name, hex=f.hex) for f in neutrals],
        styles=[
            GuideStyleOut(
                id=g.style.id,
                name=g.style.name,
                description=g.style.description,
                colors=[
                    FamilyOut(id=c, name=s.families[c].name, hex=s.families[c].hex)
                    for c in g.style.signals.get("colors", [])
                    if c in s.families
                ],
                fabrics=[fabric_names.get(f, f) for f in g.style.signals.get("fabrics", [])],
                pieces=[
                    StylePieceOut(
                        staple=staples[p.staple.id],
                        owned=names.brief(p.owned, photos.get(p.owned.id)) if p.owned else None,
                    )
                    for p in g.pieces
                ],
                chosen=g.style.id in s.profile.style_profile_ids,
            )
            for g in styles
        ],
    )
