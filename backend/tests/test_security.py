from app.core.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)


def test_a_password_hash_is_argon2id_and_checks_only_the_right_password() -> None:
    hashed = hash_password("correct horse battery staple")

    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, "correct horse battery staple")
    assert not verify_password(hashed, "Correct horse battery staple")


def test_a_damaged_hash_never_verifies() -> None:
    assert not verify_password("not a hash", "anything")


def test_session_tokens_are_long_random_and_hashed_consistently() -> None:
    first, second = new_session_token(), new_session_token()

    assert first != second
    assert len(first) >= 43  # 32 random bytes, base64url
    assert hash_session_token(first) == hash_session_token(first)
    assert hash_session_token(first) != first
