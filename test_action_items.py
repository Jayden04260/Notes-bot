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


def test_ignores_conversational_set_phrases():
    # All flagged by the original keyword list ("going to", "can you", "need to", "will").
    lines = [
        ("You", "I'm going to be honest, I didn't love the first draft."),
        ("Them", "Can you hear me okay?"),
        ("Them", "It's going to rain all week apparently."),
        ("You", "I will say the numbers look better than expected."),
        ("Them", "Let's be real, nobody reads those reports."),
        ("You", "We'll see."),
    ]
    assert find_action_items(lines) == []


def test_finds_polite_requests_and_due_dates():
    lines = [
        ("Them", "Please send me the invoice."),
        ("You", "Would you mind checking the numbers again?"),
        ("Them", "Remind me to call the supplier tomorrow."),
        ("You", "The report is due on the 14th."),
        ("Them", "Let me check with my manager and get back to you."),
    ]
    assert find_action_items(lines) == lines


def test_third_person_going_to_is_not_a_commitment():
    assert find_action_items([("Them", "They're going to love it.")]) == []
    assert find_action_items([("You", "I'm going to draft the proposal this afternoon.")]) != []
