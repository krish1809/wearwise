"""Password hashing and session tokens."""

import hashlib
import secrets
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# Argon2id with the library's defaults (RFC 9106's low-memory profile: 64 MiB, 3 passes).
# It is slow and memory-hungry on purpose, so a stolen hash is expensive to guess.
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerificationError, InvalidHashError:
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """True when the hash was made with older settings; rehash it at the next login."""
    return _hasher.check_needs_rehash(password_hash)


@lru_cache
def _dummy_hash() -> str:
    return _hasher.hash("not anyone's password")


def burn_password_check(password: str) -> None:
    """Spend the same time as a real check, so a missing account can't be spotted by timing."""
    verify_password(_dummy_hash(), password)


def new_session_token() -> str:
    """256 random bits for the cookie. Only its hash is stored."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    # A plain hash is enough: the token is random, so there's nothing to guess from the hash.
    return hashlib.sha256(token.encode()).hexdigest()
