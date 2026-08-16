from redact import redact


def test_redacts_ssn():
    text = "My SSN is 123-45-6789, keep that private."
    assert redact(text) == "My SSN is [REDACTED-SSN], keep that private."


def test_redacts_valid_card_number():
    text = "The card number is 4111 1111 1111 1111 for the order."
    assert redact(text) == "The card number is [REDACTED-CARD] for the order."


def test_does_not_redact_numbers_that_fail_luhn_check():
    text = "The tracking number is 1234567890123456."
    assert redact(text) == text


def test_does_not_redact_short_numbers_like_phone_numbers():
    text = "Call me at 555-123-4567 tomorrow."
    assert redact(text) == text


def test_leaves_ordinary_text_unchanged():
    text = "We can push the launch date to next Friday."
    assert redact(text) == text
