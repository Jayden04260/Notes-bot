from numeric_mentions import find_numbers


def test_finds_dollar_amount():
    lines = [("You", "The quote came in at $4,500 for the first phase.")]
    result = find_numbers(lines)
    assert result == [("You", "$4,500", "Money", "The quote came in at $4,500 for the first phase.")]


def test_finds_worded_currency():
    lines = [("Them", "We budgeted 250 dollars for that.")]
    result = find_numbers(lines)
    assert result == [("Them", "250 dollars", "Money", "We budgeted 250 dollars for that.")]


def test_finds_percentage():
    lines = [("You", "Churn dropped by 15% last quarter.")]
    result = find_numbers(lines)
    assert result == [("You", "15%", "Percentage", "Churn dropped by 15% last quarter.")]


def test_finds_worded_percent():
    lines = [("Them", "That's about 20 percent higher.")]
    result = find_numbers(lines)
    assert result == [("Them", "20 percent", "Percentage", "That's about 20 percent higher.")]


def test_multiple_matches_same_line():
    lines = [("You", "Revenue is up 10% to $12k this month.")]
    result = find_numbers(lines)
    assert result == [
        ("You", "10%", "Percentage", "Revenue is up 10% to $12k this month."),
        ("You", "$12k", "Money", "Revenue is up 10% to $12k this month."),
    ]


def test_ignores_plain_numbers():
    lines = [("You", "Can you send over page 3 of the deck, there's 2 of us on this."), ("Them", "Sure thing.")]
    assert find_numbers(lines) == []


def test_preserves_order_across_lines():
    lines = [
        ("You", "First offer was $100."),
        ("Them", "No numbers here."),
        ("You", "We countered at $150."),
    ]
    result = find_numbers(lines)
    assert result == [
        ("You", "$100", "Money", "First offer was $100."),
        ("You", "$150", "Money", "We countered at $150."),
    ]
