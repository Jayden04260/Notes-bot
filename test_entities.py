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


def test_clean_mention_strips_possessives_and_drops_lowercase_non_dates():
    from entities import clean_mention

    assert clean_mention("Frederick Leighton's", "PERSON") == "Frederick Leighton"
    assert clean_mention("us", "GPE") is None
    assert clean_mention("next friday", "DATE") == "next friday"
    assert clean_mention("London", "GPE") == "London"
