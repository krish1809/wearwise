"""Setting a new password from a link sent by email (M12, with the weekly email's pieces; D57).

Asking always gets the same answer, whether or not there's an account, so the form can't be used
to find out who has one. The link works once, for an hour. Using it sets the new password, counts
as confirming the address, and logs out every session, in case someone else had the old one.
"""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.adapters.email import Email, EmailSender
from app.core.config import get_settings
from app.core.security import hash_password
from app.models import User, UserSession
from app.services import auth, email_tokens, mail
from app.services.email_layout import Letter


def request(db: Session, sender: EmailSender, email: str, now: datetime) -> None:
    """Send a reset link if the address has an account (never a demo's). The caller commits."""
    user = db.scalar(select(User).where(User.email == auth.normalize_email(email)))
    if user is None or user.is_demo:
        return
    token = email_tokens.issue(db, user, "password_reset", now)
    mail.send(db, sender, reset_email(user, token), "password_reset", now, user.id)


def reset(db: Session, token: str, password: str, now: datetime) -> User | None:
    """Set the new password; None for a link that's expired, used, or made up. The caller
    checks the password against the policy first, and commits."""
    user = email_tokens.redeem(db, token, "password_reset", now)
    if user is None:
        return None
    user.password_hash = hash_password(password)
    user.email_verified_at = user.email_verified_at or now
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    return user


def reset_email(user: User, token: str) -> Email:
    url = f"{get_settings().app_url}/reset-password?token={token}"
    letter = Letter()
    letter.paragraph(
        "Someone, we hope you, asked to set a new password for the WearWise account with this "
        "address. Follow this link to choose one."
    )
    letter.link("Set a new password", url)
    letter.small(
        "The link works once, for an hour. If you didn't ask, ignore this email: your password "
        "stays as it is."
    )
    text, html = letter.finish()
    return Email(to=user.email, subject="Set a new WearWise password", text=text, html=html)
