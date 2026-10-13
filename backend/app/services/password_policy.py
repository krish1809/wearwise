"""The rules a new password must meet."""

# The sign-up form checks the same number (frontend/lib/auth.ts).
MIN_LENGTH = 12


def password_problem(password: str) -> str | None:
    """Say what's wrong with a new password, or return None if it's acceptable.

    Length is the only rule: no required digits, capitals, or symbols, which make passwords
    harder to remember without making them much harder to guess. Spaces count, so a
    passphrase works. The message is shown under the password field.
    """
    if len(password) < MIN_LENGTH:
        return f"Use at least {MIN_LENGTH} characters."
    return None
