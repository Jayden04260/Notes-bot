from translate import translate_segments, translate_text


def test_translate_segments_translates_text_field_only():
    segments = [(0.0, 1.0, "You", "hello"), (1.0, 2.0, "Them", "goodbye")]

    result = translate_segments(segments, "es", translate_fn=lambda text, tgt, src: text.upper())

    assert result == [(0.0, 1.0, "You", "HELLO"), (1.0, 2.0, "Them", "GOODBYE")]


def test_translate_segments_passes_target_and_source_lang():
    seen = []

    def fake_translate(text, target_lang, source_lang):
        seen.append((text, target_lang, source_lang))
        return text

    translate_segments([(0.0, 1.0, "You", "hi")], "fr", source_lang="en", translate_fn=fake_translate)

    assert seen == [("hi", "fr", "en")]


def test_translate_text_falls_back_to_original_on_repeated_failure(monkeypatch):
    from deep_translator.exceptions import RequestError

    class FailingTranslator:
        def __init__(self, source, target):
            pass

        def translate(self, text):
            raise RequestError("boom")

    monkeypatch.setattr("translate.GoogleTranslator", FailingTranslator)
    monkeypatch.setattr("translate.time.sleep", lambda _seconds: None)

    result = translate_text("hello", "es", retries=1)

    assert result == "hello"


def test_translate_text_returns_translation_on_success(monkeypatch):
    class FakeTranslator:
        def __init__(self, source, target):
            pass

        def translate(self, text):
            return "hola"

    monkeypatch.setattr("translate.GoogleTranslator", FakeTranslator)

    assert translate_text("hello", "es") == "hola"
