"""The weekly email (docs/AGENTS.md, section 5), built from a digest's rows, so it says exactly
what the Weekly picks page says. Words, colour dots, and links: never the person's photos (they're
private) or images from articles (they aren't WearWise's).

Every email has a signed "not for me" link for each pick, a signed unsubscribe link, and the
one-click unsubscribe headers mail apps show as a button (RFC 8058). Until WearWise's email
domain is verified, it says it's a preview.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.email import Email
from app.core.config import get_settings
from app.models import ColorFamily, Digest, DigestPick, User
from app.services import digests, email_links
from app.services.email_layout import Letter


def rupees(paise: int) -> str:
    """₹1,500 or ₹1,50,000: the Indian way of grouping digits."""
    whole, fraction = divmod(paise, 100)
    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join([*groups, tail])
    return f"₹{digits}" + (f".{fraction:02d}" if fraction else "")


def render(db: Session, digest: Digest, user: User) -> Email:
    settings = get_settings()
    app = settings.app_url
    preview = bool(settings.email_allowed)
    hexes = {family.id: family.hex for family in db.scalars(select(ColorFamily))}
    unsubscribe = email_links.sign("unsubscribe", str(user.id))
    picks = [p for p in digests.picks_of(db, digest) if p.verdict is None]

    letter = Letter()
    if preview:
        letter.small(
            "A preview: until WearWise's email is set up for everyone, this goes only to the "
            "addresses on its list."
        )
    letter.paragraph(digest.intro)
    for n, pick in enumerate(picks, start=1):
        _pick(letter, n, pick, hexes, app)
    if not picks:
        letter.paragraph(digests.note_text(digest.note) or "Nothing worth buying this week.")
    letter.link("See your picks, with your own pieces", f"{app}/picks")
    letter.small(
        "You get this because you turned on the weekly email in WearWise. Change the day or "
        "turn it off in Settings."
    )
    letter.link("Settings", f"{app}/settings")
    letter.link("Unsubscribe", f"{app}/unsubscribe?token={unsubscribe}")
    text, html = letter.finish()
    return Email(
        to=user.email,
        subject=("Preview: " if preview else "") + digest.subject,
        text=text,
        html=html,
        headers={
            "List-Unsubscribe": f"<{app}/api/v1/email/unsubscribe/one-click?token={unsubscribe}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
        key=f"digest-{digest.id}",
    )


def _pick(letter: Letter, n: int, pick: DigestPick, hexes: dict[str, str | None], app: str) -> None:
    letter.heading(f"{n}. {pick.name}", hexes.get(pick.color_primary))
    letter.paragraph(f"In fashion now: {pick.trend_name}. {pick.trend_summary}")
    letter.paragraph(pick.text)
    if pick.links:
        lead = "Look for it"
        if pick.usual_spend:
            lead += f" (you usually spend up to {rupees(pick.usual_spend)})"
        letter.links(lead + ":", [(link["shop"], link["url"]) for link in pick.links])
    token = email_links.sign("not_for_me", str(pick.id))
    letter.link("Not for me", f"{app}/not-for-me?token={token}")
