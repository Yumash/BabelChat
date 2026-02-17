"""Tests for built-in phrase dictionary."""

from app.phrasebook import _normalize, lookup, lookup_abbreviation, stats


class TestNormalize:
    """Test text normalization for lookup."""

    def test_lowercase(self):
        assert _normalize("Hello") == "hello"

    def test_strip_trailing_punctuation(self):
        assert _normalize("hi!") == "hi"
        assert _normalize("thanks.") == "thanks"
        assert _normalize("ready?") == "ready"

    def test_strip_multiple_trailing_punct(self):
        assert _normalize("help!!!") == "help"

    def test_preserve_mid_word_apostrophe(self):
        assert _normalize("i'm ready") == "i'm ready"
        assert _normalize("what's up") == "what's up"
        assert _normalize("you're welcome") == "you're welcome"

    def test_strip_whitespace(self):
        assert _normalize("  hello  ") == "hello"

    def test_combined(self):
        assert _normalize("  Thank You!  ") == "thank you"


class TestLookup:
    """Test phrasebook lookup."""

    def test_basic_en_to_ru(self):
        assert lookup("hello", "EN", "RU") == "привет"

    def test_basic_ru_to_en(self):
        result = lookup("спасибо", "RU", "EN")
        assert result in ("thanks", "thank you", "thx")

    def test_de_to_ru(self):
        assert lookup("danke", "DE", "RU") is not None

    def test_fr_to_ru(self):
        assert lookup("merci", "FR", "RU") is not None

    def test_es_to_en(self):
        assert lookup("gracias", "ES", "EN") is not None

    def test_case_insensitive(self):
        assert lookup("Hello", "EN", "RU") == lookup("hello", "EN", "RU")
        assert lookup("THANKS", "EN", "RU") == lookup("thanks", "EN", "RU")

    def test_punctuation_insensitive(self):
        assert lookup("hello!", "EN", "RU") == lookup("hello", "EN", "RU")
        assert lookup("thanks.", "EN", "RU") == lookup("thanks", "EN", "RU")

    def test_miss_returns_none(self):
        assert lookup("supercalifragilistic", "EN", "RU") is None

    def test_wrong_lang_pair_returns_none(self):
        assert lookup("hello", "JA", "RU") is None

    def test_lang_codes_case_insensitive(self):
        assert lookup("hello", "en", "ru") == lookup("hello", "EN", "RU")

    def test_gaming_phrases(self):
        assert lookup("ready", "EN", "RU") == "готов"
        assert lookup("wait", "EN", "RU") == "подожди"
        assert lookup("let's go", "EN", "RU") == "погнали"

    def test_wow_specific(self):
        assert lookup("good luck", "EN", "RU") == "удачи"
        assert lookup("good run", "EN", "RU") == "хороший ран"

    def test_questions(self):
        assert lookup("how are you", "EN", "RU") == "как дела"
        assert lookup("where are you", "EN", "RU") == "где ты"


class TestAbbreviations:
    """Test universal gaming abbreviation lookup."""

    def test_gg_to_ru(self):
        assert lookup_abbreviation("gg", "RU") == "хорошая игра"

    def test_bb_to_ru(self):
        assert lookup_abbreviation("bb", "RU") == "пока"

    def test_afk_to_ru(self):
        assert lookup_abbreviation("afk", "RU") == "отошёл"

    def test_brb_to_ru(self):
        assert lookup_abbreviation("brb", "RU") == "скоро вернусь"

    def test_ty_to_ru(self):
        assert lookup_abbreviation("ty", "RU") == "спасибо"

    def test_np_to_ru(self):
        assert lookup_abbreviation("np", "RU") == "без проблем"

    def test_omw_to_ru(self):
        assert lookup_abbreviation("omw", "RU") == "иду"

    def test_oom_to_de(self):
        assert lookup_abbreviation("oom", "DE") == "kein Mana"

    def test_idk_to_ru(self):
        assert lookup_abbreviation("idk", "RU") == "не знаю"

    def test_btw_to_ru(self):
        assert lookup_abbreviation("btw", "RU") == "кстати"

    def test_case_insensitive(self):
        assert lookup_abbreviation("GG", "RU") == lookup_abbreviation("gg", "RU")
        assert lookup_abbreviation("AFK", "RU") == lookup_abbreviation("afk", "RU")

    def test_miss_returns_none(self):
        assert lookup_abbreviation("xyz123", "RU") is None

    def test_abbreviation_via_lookup(self):
        """Abbreviations should also work through the main lookup function."""
        assert lookup("gg", "EN", "RU") == "хорошая игра"
        assert lookup("brb", "DE", "RU") == "скоро вернусь"

    def test_abbreviation_to_different_languages(self):
        assert lookup_abbreviation("ty", "DE") == "danke"
        assert lookup_abbreviation("ty", "FR") == "merci"
        assert lookup_abbreviation("ty", "ES") == "gracias"


class TestStats:
    """Test phrasebook statistics."""

    def test_has_entries(self):
        s = stats()
        assert s["entries"] > 0
        assert s["unique_phrases"] > 0
        assert s["languages"] >= 2

    def test_multiple_languages(self):
        s = stats()
        assert s["languages"] >= 5
