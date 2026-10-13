from app.services.password_policy import MIN_LENGTH, password_problem


def test_a_password_one_character_too_short_is_rejected() -> None:
    assert password_problem("a" * (MIN_LENGTH - 1)) == "Use at least 12 characters."


def test_a_password_exactly_at_the_minimum_is_accepted() -> None:
    assert password_problem("a" * MIN_LENGTH) is None


def test_a_passphrase_with_spaces_is_accepted() -> None:
    assert password_problem("correct horse battery staple") is None


def test_letters_alone_are_enough() -> None:
    # No composition rules: no digits, capitals, or symbols required.
    assert password_problem("onlylowercaseletters") is None


def test_spaces_are_not_trimmed_away() -> None:
    # Eleven letters plus a space is twelve characters, exactly as typed.
    assert password_problem("elevenchars ") is None
    assert password_problem(" " * (MIN_LENGTH - 1)) == "Use at least 12 characters."
