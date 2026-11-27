"""Sending email (docs/AGENTS.md, section 7; D57).

One interface, three settings: Resend over HTTPS with Python's own HTTP client (no SDK), the
console in development (the email is written to the log), and a fake that keeps what it was
given, for tests. A timeout, and one retry when the service is busy or erring; anything else is
EmailUnavailable, and the caller records it.

Who may be emailed is decided before this, in app/services/mail.py: confirmed addresses only,
the allowlist until a domain is verified, and the daily cap.
"""

import json
import logging
import urllib.error
import urllib.request
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import get_settings

log = logging.getLogger(__name__)

API_URL = "https://api.resend.com/emails"
TIMEOUT_SECONDS = 20
ATTEMPTS = 2
RETRY_STATUSES = {429, 500, 502, 503, 504}
USER_AGENT = "WearWise/1.0"


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    text: str
    html: str
    headers: Mapping[str, str] = field(default_factory=dict)
    # The provider sends one email per key, so a send retried within a day can't arrive twice.
    key: str | None = None


class EmailUnavailable(Exception):
    """The email service didn't answer, or refused the email."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class EmailSender(Protocol):
    def send(self, email: Email) -> str:
        """Send it; returns the provider's id for the email."""
        ...


class ResendEmail:
    def __init__(self, key: str, sender: str) -> None:
        self._key = key
        self._sender = sender

    def send(self, email: Email) -> str:
        body: dict[str, Any] = {
            "from": self._sender,
            "to": [email.to],
            "subject": email.subject,
            "text": email.text,
            "html": email.html,
        }
        if email.headers:
            body["headers"] = dict(email.headers)
        headers = {
            "authorization": f"Bearer {self._key}",
            "content-type": "application/json",
            "user-agent": USER_AGENT,
        }
        if email.key:
            headers["idempotency-key"] = email.key
        payload = json.dumps(body).encode()
        for attempt in range(ATTEMPTS):
            request = urllib.request.Request(API_URL, data=payload, method="POST", headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                    data: dict[str, Any] = json.loads(response.read())
                    return str(data["id"])
            except urllib.error.HTTPError as error:
                log.warning("Email service answered %s", error.code)
                if error.code not in RETRY_STATUSES or attempt == ATTEMPTS - 1:
                    raise EmailUnavailable("refused" if error.code < 500 else "down") from error
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as error:
                log.warning("Email service unreachable: %s", error)
                if attempt == ATTEMPTS - 1:
                    raise EmailUnavailable("down") from error
        raise EmailUnavailable("down")  # pragma: no cover


class ConsoleEmail:
    """Development: the email is written to the log instead of being sent. In production it
    sends nothing and says nothing about the email (its address and links stay out of the
    logs): email isn't set up there until EMAIL_PROVIDER is."""

    def __init__(self, production: bool = False) -> None:
        self._production = production

    def send(self, email: Email) -> str:
        if self._production:
            log.warning("An email wasn't sent: EMAIL_PROVIDER isn't set up")
            raise EmailUnavailable("not_set_up")
        log.info("Email to %s: %s\n\n%s", email.to, email.subject, email.text)
        return f"console-{uuid.uuid4()}"


@dataclass
class FakeEmail:
    """For tests: keeps every email; `down` makes every send fail."""

    sent: list[Email] = field(default_factory=list)
    down: bool = False

    def send(self, email: Email) -> str:
        if self.down:
            raise EmailUnavailable("down")
        self.sent.append(email)
        return f"fake-{len(self.sent)}"


@lru_cache
def get_email_sender() -> EmailSender:
    settings = get_settings()
    if settings.email_provider == "resend":
        return ResendEmail(settings.email_api_key or "", settings.email_from or "")
    if settings.email_provider == "fake":
        return FakeEmail()
    return ConsoleEmail(production=settings.is_production)
