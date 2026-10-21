"""Links in emails that work without logging in (D57): unsubscribe, and "not for me" on a pick.

Each carries what it's for and a signature (HMAC-SHA256 with EMAIL_LINK_SECRET), so it does that
one thing for that one account or pick, and can't be made up for another. They don't expire: an
unsubscribe link in an old email must still work. Links that should work once (confirming an
address, a new password) are single-use tokens instead (app/services/email_tokens.py).
"""

import base64
import binascii
import hashlib
import hmac

from app.core.config import ConfigError, get_settings

# Local development signs with this when no secret is set; production never does.
DEVELOPMENT_SECRET = "wearwise-development-only"
# 128 bits of the signature: plenty against guessing, and the links stay short.
SIGNATURE_BYTES = 16


def _secret() -> bytes | None:
    settings = get_settings()
    if settings.email_link_secret:
        return settings.email_link_secret.encode()
    return None if settings.is_production else DEVELOPMENT_SECRET.encode()


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _signature(secret: bytes, message: bytes) -> bytes:
    return hmac.new(secret, message, hashlib.sha256).digest()[:SIGNATURE_BYTES]


def sign(purpose: str, value: str) -> str:
    """A token that says `purpose` for `value` (an account's or a pick's id)."""
    secret = _secret()
    if secret is None:
        raise ConfigError("EMAIL_LINK_SECRET is needed to put links in emails")
    message = f"{purpose}:{value}".encode()
    return f"{_encode(message)}.{_encode(_signature(secret, message))}"


def verify(token: str, purpose: str) -> str | None:
    """The value a genuine token for `purpose` carries; None for anything else."""
    secret = _secret()
    if secret is None:
        return None
    encoded, _, signature = token.partition(".")
    try:
        message = _decode(encoded)
        given = _decode(signature)
    except binascii.Error, ValueError:
        return None
    if not hmac.compare_digest(_signature(secret, message), given):
        return None
    found, _, value = message.decode(errors="replace").partition(":")
    return value if found == purpose and value else None
