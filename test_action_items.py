from action_items import find_action_items


def test_finds_commitment_phrases():
    lines = [
        ("You", "I'll send the deck over tonight."),
        ("Them", "Sounds good, thanks."),
    ]
    result = find_action_items(lines)
    assert result == [("You", "I'll send the deck over tonight.")]


def test_finds_request_and_deadline_phrases():
    lines = [
        ("Them", "Can you review the proposal by Friday?"),
        ("You", "The weather has been nice lately."),
    ]
    result = find_action_items(lines)
    assert result == [("Them", "Can you review the proposal by Friday?")]


def test_ignores_lines_with_no_action_language():
    lines = [
        ("You", "That makes sense."),
        ("Them", "Yeah, agreed."),
    ]
    assert find_action_items(lines) == []


def test_preserves_order_and_speaker():
    lines = [
        ("You", "Let's circle back next week."),
        ("Them", "No action here."),
        ("Them", "I will follow up with finance."),
    ]
    result = find_action_items(lines)
    assert result == [
        ("You", "Let's circle back next week."),
        ("Them", "I will follow up with finance."),
    ]
