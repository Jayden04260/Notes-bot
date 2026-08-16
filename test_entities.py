from entities import extract_entities


def test_extracts_person_and_org():
    text = "John Smith from Acme Corp said the deadline is next Friday."
    result = extract_entities(text)
    assert "John Smith" in result.get("People", [])
    assert "Acme Corp" in result.get("Organizations", [])


def test_extracts_place():
    text = "Sarah is based in London this quarter."
    result = extract_entities(text)
    assert "London" in result.get("Places", [])


def test_dedupes_repeated_mentions():
    text = "Acme Corp approved the budget. Acme Corp will follow up next week."
    result = extract_entities(text)
    assert result["Organizations"].count("Acme Corp") == 1


def test_empty_text_returns_empty_dict():
    assert extract_entities("") == {}
    assert extract_entities("   ") == {}
