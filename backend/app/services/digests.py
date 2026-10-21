"""This week's picks for one person (docs/AGENTS.md, section 5).

Gather what they've told WearWise and the trends approved for their sections, turn each trend
into a piece they could buy, let the engine pick (app/engine/digest.py), add where to look, and
word each pick from its numbers. The weekly email has the model reword it, checked against the
same numbers; this wording is what it falls back to, and what the page shows until then.

Nothing here is invented: the pieces come from the trends' own attributes and the categories'
defaults, the numbers from the purchase analyzer, the links from the shop-search adapter, and
the usual spend from the person's own answers.
"""

import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.products import search_links
from app.engine import digest as engine
from app.engine import shopping as analyzer
from app.engine.config import DEFAULT
from app.engine.generate import season_for
from app.models import Digest, DigestPick, Profile, Trend, User
from app.services import email_links, reference, shopping

# The season ahead is read this far on, as the Trend Scout reads it.
AHEAD = timedelta(weeks=4)
SECTION_WORDS = {"menswear": "men", "womenswear": "women"}
NOTES = {
    "no_occasions": "Choose the occasions you dress for first, so picks can be judged against "
    "what you'd wear them to.",
    "no_trends": "No trends have been approved for your sections yet.",
    "nothing_worth_it": "Nothing in fashion now would add much to what you own. That's a good "
    "week to buy nothing.",
}


def week_of(day: date) -> str:
    """The ISO week a day is in, such as 2026-W44."""
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def _short(name: str) -> str:
    # "Sage / mint" -> "Sage"; "Co-ord set (worn as one)" -> "Co-ord set".
    return name.split(" / ")[0].split(" (")[0]


def approved_trends(db: Session, profile: Profile) -> list[Trend]:
    """Approved trends for the person's sections (every section's, when none are chosen)."""
    rows = db.scalars(
        select(Trend).where(Trend.status == "approved").order_by(Trend.last_seen_at.desc())
    )
    sections = set(profile.sections)
    return [t for t in rows if not sections or not t.sections or sections & set(t.sections)]


def options_for(db: Session, s: shopping.Setting, trends: list[Trend]) -> list[engine.TrendOption]:
    """Each trend as pieces the person could buy: one per category it names that fits their
    sections, in the trend's colour they prefer (or its first they don't avoid), with its first
    fabric, pattern, and fit. A trend that names no colour takes the usual colour of the
    category's staple; one whose colours are all avoided isn't for them."""
    profile = s.profile
    avoided = set(profile.avoided_colors)
    preferred = set(profile.preferred_colors)
    sections = set(profile.sections)
    fabrics = {term.id: term.name for term in reference.terms(db, "fabric")}
    staple_colours: dict[str, str] = {}
    for staple in shopping.staples(db, profile):
        if staple.color not in avoided:
            staple_colours.setdefault(staple.category_id, staple.color)
    found: list[engine.TrendOption] = []
    for trend in trends:
        colours = [c for c in trend.color_families if c in s.families and c not in avoided]
        colours.sort(key=lambda c: c not in preferred)
        if trend.color_families and not colours:
            continue
        fabric = trend.fabrics[0] if trend.fabrics else None
        for category_id in trend.category_ids:
            category = s.categories.get(category_id)
            if category is None or category.user_id is not None:
                continue
            if sections and category.sections and not sections & set(category.sections):
                continue
            colour = colours[0] if colours else staple_colours.get(category_id)
            if colour is None:
                continue
            name = _piece_name(s, colour, fabrics.get(fabric or ""), category_id)
            found.append(
                engine.TrendOption(
                    trend_id=str(trend.id),
                    candidate=shopping.piece_item(
                        s,
                        f"trend:{trend.id}:{category_id}",
                        name,
                        category_id,
                        colour,
                        trend.patterns[0] if trend.patterns else "solid",
                        fabric,
                        trend.fits[0] if trend.fits else None,
                        list(trend.seasons),
                    ),
                    styles=frozenset(trend.style_profile_ids),
                    colors=frozenset(trend.color_families),
                    seasons=frozenset(trend.seasons),
                )
            )
    return found


def _piece_name(s: shopping.Setting, colour: str, fabric: str | None, category_id: str) -> str:
    """ "Olive cotton chinos": colour, fabric (unless the category already says it), category."""
    category = _short(s.categories[category_id].name)
    words = [_short(s.families[colour].name)]
    if fabric and fabric.lower() not in category.lower():
        words.append(fabric.lower())
    words.append(category[:1].lower() + category[1:])
    return " ".join(words)


def declined(db: Session, user: User, today: date) -> tuple[engine.Declined, ...]:
    """Every pick the person said "not for me" to, and how long ago."""
    rows = db.scalars(
        select(DigestPick)
        .join(Digest, Digest.id == DigestPick.digest_id)
        .where(Digest.user_id == user.id, DigestPick.verdict == "not_for_me")
    )
    return tuple(
        engine.Declined(
            trend_id=str(row.trend_id) if row.trend_id else f"removed:{row.id}",
            category_id=row.category_id,
            color_family=row.color_primary,
            days_ago=(today - (row.verdict_at or row.created_at).date()).days,
        )
        for row in rows
    )


def build(db: Session, user: User, now: datetime, week: str | None = None) -> Digest:
    """This week's digest (or `week`'s), worked out now. One already sent stays as it was sent.
    One only built is worked out again, keeping the picks the person said "not for me" to, so
    that answer still counts. The caller commits.

    The weekly email passes the week of the person's own email day, so an email sent a day
    late, after the week has turned, still belongs to the week it was for."""
    today = now.date()
    week = week or week_of(today)
    existing = db.scalar(select(Digest).where(Digest.user_id == user.id, Digest.week == week))
    if existing is not None and existing.status == "sent":
        return existing
    kept: list[DigestPick] = []
    if existing is not None:
        for old in picks_of(db, existing):
            if old.verdict is None:
                db.delete(old)
            else:
                kept.append(old)
        # Out of the way of the new picks' positions; put back after them below.
        for n, old in enumerate(kept):
            old.position = 1000 + n
        db.flush()

    s = shopping.setting(db, user, today)
    seasons = {term.id: term.name for term in reference.terms(db, "season")}
    season = s.base.season or season_for(today)
    picks: list[engine.Pick] = []
    trends: dict[str, Trend] = {}
    note: str | None = None
    if s.before is None:
        note = "no_occasions"
    else:
        found_trends = approved_trends(db, s.profile)
        trends = {str(trend.id): trend for trend in found_trends}
        if not found_trends:
            note = "no_trends"
        else:
            person = engine.Person(
                styles=frozenset(s.profile.style_profile_ids),
                preferred_colors=frozenset(s.profile.preferred_colors),
                avoided_colors=frozenset(s.profile.avoided_colors),
                season_now=season,
                season_ahead=season_for(today + AHEAD),
                declined=declined(db, user, today),
            )
            line = analyzer.buy_line(shopping.gaps(db, s))
            names = {item.id: item.name for item in s.wardrobe.items}
            picks = engine.pick(
                options_for(db, s, found_trends),
                person,
                s.wardrobe,
                s.base,
                s.engine_occasions,
                s.seasons,
                s.before,
                line,
                names,
                DEFAULT,
                s.pairs(),
            )
            if not picks:
                note = "nothing_worth_it"

    season_name = seasons.get(season, season).lower()
    digest = existing or Digest(user_id=user.id, week=week)
    digest.status = "built" if picks else "nothing"
    digest.note = note
    digest.season = season
    digest.subject = _subject(picks)
    digest.intro = (
        f"What's in fashion in India this {season_name} season, judged against what you "
        "already own."
    )
    digest.wording = "template"
    db.add(digest)
    db.flush()
    owned_ids = {item.id for item in s.wardrobe.items if item.owner_id == str(user.id)}
    names = {item.id: item.name for item in s.wardrobe.items}
    for position, found in enumerate(picks):
        trend = trends[found.trend_id]
        db.add(_pick_row(s, digest, position, found, trend, owned_ids, names))
    for n, old in enumerate(kept):
        old.position = len(picks) + n
    db.flush()
    return digest


def _subject(picks: list[engine.Pick]) -> str:
    buys = [p for p in picks if p.kind == "buy"]
    if buys:
        more = f" and {len(picks) - 1} more" if len(picks) > 1 else ""
        return f"Worth a look this week: {buys[0].item.name.lower()}{more}"
    if picks:
        return "This week, what's in fashion is already in your wardrobe"
    return "Nothing worth buying this week"


def _pick_row(
    s: shopping.Setting,
    digest: Digest,
    position: int,
    found: engine.Pick,
    trend: Trend,
    owned_ids: set[str],
    names: dict[str, str],
) -> DigestPick:
    item = found.item
    category = s.categories[item.category_id]
    worn_with = [i for i in found.outfit if i in owned_ids and i != item.id]
    row = DigestPick(
        digest_id=digest.id,
        position=position,
        kind=found.kind,
        trend_id=trend.id,
        trend_name=trend.name,
        trend_summary=trend.summary,
        name=item.name[:1].upper() + item.name[1:],
        category_id=item.category_id,
        color_primary=item.color_family,
        score=found.score,
        components={
            "value": found.value,
            "trend_fit": found.trend_fit,
            "season_fit": found.season_fit,
        },
        usual_spend=s.profile.category_budgets.get(category.group_id),
    )
    if found.kind == "owned":
        row.item_ids = [uuid.UUID(i) for i in (item.id, *worn_with)]
        row.text = f"You already have one: your {_lower(item.name)}."
        if worn_with:
            row.text += f" Wear it with your {_listing([_lower(names[i]) for i in worn_with])}."
        return row
    analysis = found.analysis
    assert analysis is not None and found.verdict is not None
    row.item_ids = [uuid.UUID(i) for i in worn_with]
    row.attrs = {
        "fabric": item.fabric,
        "pattern": item.pattern,
        "fit": item.fit,
        "seasons": sorted(item.seasons),
    }
    row.analysis = {
        "verdict": found.verdict.code,
        "kind": analysis.kind,
        "new_outfits": analysis.new_outfits,
        "coverage_gain": analysis.coverage_gain,
        "redundancy": analysis.redundancy,
        "reasons": [
            {"code": reason.code, "kind": reason.kind, "text": reason.text}
            for reason in found.verdict.reasons
        ],
    }
    section = SECTION_WORDS.get(s.profile.sections[0]) if len(s.profile.sections) == 1 else None
    words = [w for w in item.name.split()] + ([section] if section else [])
    row.query, links = search_links(words)
    row.links = [{"shop_id": link.shop_id, "shop": link.shop, "url": link.url} for link in links]
    row.text = f"{row.name} " + _adds(analysis)
    return row


def _adds(analysis: analyzer.Analysis) -> str:
    if analysis.kind == "core":
        return f"would make {analysis.new_outfits} new outfits with what you own."
    if analysis.kind == "accessory":
        return f"would finish {analysis.new_outfits} outfits you can already make."
    return "would be new for you."


def _lower(name: str) -> str:
    return name[:1].lower() + name[1:]


def _listing(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def note_text(note: str | None) -> str | None:
    return NOTES.get(note or "")


def latest(db: Session, user: User) -> Digest | None:
    return db.scalar(
        select(Digest).where(Digest.user_id == user.id).order_by(Digest.week.desc()).limit(1)
    )


def picks_of(db: Session, digest: Digest) -> list[DigestPick]:
    return list(
        db.scalars(
            select(DigestPick)
            .where(DigestPick.digest_id == digest.id)
            .order_by(DigestPick.position)
        )
    )


def find_pick(db: Session, user: User, pick_id: uuid.UUID) -> DigestPick | None:
    """One of the person's own picks; None for anyone else's."""
    return db.scalar(
        select(DigestPick)
        .join(Digest, Digest.id == DigestPick.digest_id)
        .where(DigestPick.id == pick_id, Digest.user_id == user.id)
    )


def react_by_link(db: Session, token: str, now: datetime) -> DigestPick | None:
    """ "Not for me" from the link in an email, which works without logging in. None for a
    token that isn't genuine, or a pick that's gone. The caller commits."""
    found = email_links.verify(token, "not_for_me")
    if found is None:
        return None
    try:
        pick = db.get(DigestPick, uuid.UUID(found))
    except ValueError:
        return None
    return react(pick, True, now) if pick is not None else None


def react(pick: DigestPick, not_for_me: bool, now: datetime) -> DigestPick:
    """ "Not for me", or taking it back. The caller commits."""
    pick.verdict = "not_for_me" if not_for_me else None
    pick.verdict_at = now if not_for_me else None
    return pick
