"""Built-in phrase dictionary for instant translation without DeepL API."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Strip trailing punctuation only — preserve mid-word apostrophes
_RE_TRAILING_PUNCT = re.compile(r"[!?.,:;\"'()]+$")

PhrasebookKey = tuple[str, str, str]  # (norm_text, src_lang, tgt_lang)

_ENTRIES: dict[PhrasebookKey, str] = {}

# Universal gaming abbreviations — keyed by (abbrev, target_lang)
_ABBREVIATIONS: dict[tuple[str, str], str] = {}


def _normalize(text: str) -> str:
    """Lowercase, strip trailing punctuation."""
    return _RE_TRAILING_PUNCT.sub("", text.strip().lower())


def _add(phrase_map: dict[str, str]) -> None:
    """Register a phrase across all language pair combinations."""
    langs = list(phrase_map.items())
    for i, (src_lang, src_text) in enumerate(langs):
        for j, (tgt_lang, tgt_text) in enumerate(langs):
            if i != j:
                _ENTRIES[(_normalize(src_text), src_lang, tgt_lang)] = tgt_text


def _abbrev(abbr: str, translations: dict[str, str]) -> None:
    """Register a universal gaming abbreviation."""
    norm = _normalize(abbr)
    for lang, text in translations.items():
        _ABBREVIATIONS[(norm, lang)] = text


# ---------------------------------------------------------------------------
# Phrase data: {lang_code: phrase_text}
# Languages: EN, RU, DE, FR, ES
# fmt: off
# ---------------------------------------------------------------------------

# --- Greetings ---
_add({"EN": "hello", "RU": "привет",
      "DE": "hallo", "FR": "bonjour", "ES": "hola"})
_add({"EN": "hey", "RU": "привет",
      "DE": "hey", "FR": "salut", "ES": "hey"})
_add({"EN": "good morning", "RU": "доброе утро",
      "DE": "guten morgen", "FR": "bonjour", "ES": "buenos días"})
_add({"EN": "good evening", "RU": "добрый вечер",
      "DE": "guten abend", "FR": "bonsoir", "ES": "buenas tardes"})
_add({"EN": "good night", "RU": "спокойной ночи",
      "DE": "gute nacht", "FR": "bonne nuit", "ES": "buenas noches"})
_add({"EN": "bye", "RU": "пока",
      "DE": "tschüss", "FR": "salut", "ES": "adiós"})
_add({"EN": "goodbye", "RU": "до свидания",
      "DE": "auf wiedersehen", "FR": "au revoir", "ES": "adiós"})
_add({"EN": "see you", "RU": "увидимся",
      "DE": "bis dann", "FR": "à plus", "ES": "nos vemos"})
_add({"EN": "cya", "RU": "пока",
      "DE": "cya", "FR": "a+", "ES": "nos vemos"})
_add({"EN": "later", "RU": "позже",
      "DE": "später", "FR": "à plus tard", "ES": "luego"})
_add({"EN": "welcome", "RU": "добро пожаловать",
      "DE": "willkommen", "FR": "bienvenue", "ES": "bienvenido"})

# --- Politeness ---
_add({"EN": "thanks", "RU": "спасибо",
      "DE": "danke", "FR": "merci", "ES": "gracias"})
_add({"EN": "thank you", "RU": "спасибо",
      "DE": "danke schön", "FR": "merci", "ES": "gracias"})
_add({"EN": "thx", "RU": "спасибо",
      "DE": "danke", "FR": "merci", "ES": "gracias"})
_add({"EN": "please", "RU": "пожалуйста",
      "DE": "bitte", "FR": "s'il vous plaît", "ES": "por favor"})
_add({"EN": "pls", "RU": "пожалуйста",
      "DE": "bitte", "FR": "svp", "ES": "por favor"})
_add({"EN": "sorry", "RU": "извини",
      "DE": "sorry", "FR": "désolé", "ES": "perdón"})
_add({"EN": "no problem", "RU": "без проблем",
      "DE": "kein problem", "FR": "pas de problème",
      "ES": "no hay problema"})
_add({"EN": "you're welcome", "RU": "пожалуйста",
      "DE": "bitte schön", "FR": "de rien", "ES": "de nada"})
_add({"EN": "my bad", "RU": "моя ошибка",
      "DE": "mein fehler", "FR": "ma faute", "ES": "mi culpa"})

# --- Gaming coordination ---
_add({"EN": "ready", "RU": "готов",
      "DE": "bereit", "FR": "prêt", "ES": "listo"})
_add({"EN": "wait", "RU": "подожди",
      "DE": "warte", "FR": "attends", "ES": "espera"})
_add({"EN": "stop", "RU": "стоп",
      "DE": "stopp", "FR": "stop", "ES": "para"})
_add({"EN": "help", "RU": "помогите",
      "DE": "hilfe", "FR": "aide", "ES": "ayuda"})
_add({"EN": "follow me", "RU": "за мной",
      "DE": "folgt mir", "FR": "suivez-moi", "ES": "síganme"})
_add({"EN": "on my way", "RU": "иду",
      "DE": "bin unterwegs", "FR": "j'arrive", "ES": "voy"})
_add({"EN": "need help", "RU": "нужна помощь",
      "DE": "brauche hilfe", "FR": "besoin d'aide",
      "ES": "necesito ayuda"})
_add({"EN": "come here", "RU": "иди сюда",
      "DE": "komm her", "FR": "viens ici", "ES": "ven aquí"})
_add({"EN": "let's go", "RU": "погнали",
      "DE": "los geht's", "FR": "allons-y", "ES": "vamos"})
_add({"EN": "run", "RU": "бегите",
      "DE": "lauf", "FR": "courez", "ES": "corran"})

# --- Status ---
_add({"EN": "i'm ready", "RU": "я готов",
      "DE": "ich bin bereit", "FR": "je suis prêt",
      "ES": "estoy listo"})
_add({"EN": "i'm coming", "RU": "иду",
      "DE": "ich komme", "FR": "j'arrive", "ES": "ya voy"})
_add({"EN": "one moment", "RU": "секунду",
      "DE": "einen moment", "FR": "un moment", "ES": "un momento"})
_add({"EN": "one sec", "RU": "секунду",
      "DE": "eine sekunde", "FR": "une seconde", "ES": "un segundo"})
_add({"EN": "back", "RU": "вернулся",
      "DE": "zurück", "FR": "de retour", "ES": "volví"})
_add({"EN": "i'm back", "RU": "я вернулся",
      "DE": "bin zurück", "FR": "je suis de retour",
      "ES": "ya volví"})

# --- Reactions ---
_add({"EN": "nice", "RU": "круто",
      "DE": "nice", "FR": "cool", "ES": "genial"})
_add({"EN": "great", "RU": "отлично",
      "DE": "super", "FR": "génial", "ES": "genial"})
_add({"EN": "cool", "RU": "круто",
      "DE": "cool", "FR": "cool", "ES": "genial"})
_add({"EN": "awesome", "RU": "круто",
      "DE": "super", "FR": "génial", "ES": "increíble"})
_add({"EN": "well done", "RU": "молодец",
      "DE": "gut gemacht", "FR": "bien joué", "ES": "bien hecho"})
_add({"EN": "good job", "RU": "молодец",
      "DE": "gute arbeit", "FR": "bon travail", "ES": "buen trabajo"})

# --- Common questions ---
_add({"EN": "how are you", "RU": "как дела",
      "DE": "wie geht's", "FR": "comment ça va", "ES": "cómo estás"})
_add({"EN": "where are you", "RU": "где ты",
      "DE": "wo bist du", "FR": "où es-tu", "ES": "dónde estás"})
_add({"EN": "what's up", "RU": "как дела",
      "DE": "was geht", "FR": "quoi de neuf", "ES": "qué tal"})
_add({"EN": "do you speak english",
      "RU": "ты говоришь по-английски",
      "DE": "sprichst du englisch",
      "FR": "tu parles anglais", "ES": "hablas inglés"})

# --- WoW-specific ---
_add({"EN": "summon please", "RU": "призовите пожалуйста",
      "DE": "summon bitte", "FR": "invocation svp",
      "ES": "invocar por favor"})
_add({"EN": "invite please", "RU": "инвайт пожалуйста",
      "DE": "einladung bitte", "FR": "invite svp",
      "ES": "invitar por favor"})
_add({"EN": "good run", "RU": "хороший ран",
      "DE": "guter run", "FR": "bon run", "ES": "buen run"})
_add({"EN": "good group", "RU": "хорошая группа",
      "DE": "gute gruppe", "FR": "bon groupe", "ES": "buen grupo"})
_add({"EN": "good luck", "RU": "удачи",
      "DE": "viel glück", "FR": "bonne chance",
      "ES": "buena suerte"})
_add({"EN": "have fun", "RU": "удачи",
      "DE": "viel spaß", "FR": "amusez-vous",
      "ES": "diviértanse"})
_add({"EN": "well played", "RU": "хорошо сыграно",
      "DE": "gut gespielt", "FR": "bien joué",
      "ES": "bien jugado"})

# ---------------------------------------------------------------------------
# Gaming abbreviations — universal, language-independent
# ---------------------------------------------------------------------------

_abbrev("gg", {
    "RU": "хорошая игра", "DE": "gutes Spiel",
    "FR": "bien joué", "ES": "buen juego"})
_abbrev("bb", {
    "RU": "пока", "EN": "bye bye",
    "DE": "tschüss", "FR": "salut", "ES": "adiós"})
_abbrev("afk", {
    "RU": "отошёл", "DE": "bin weg",
    "FR": "absent", "ES": "ausente"})
_abbrev("brb", {
    "RU": "скоро вернусь", "DE": "bin gleich zurück",
    "FR": "je reviens", "ES": "ya vuelvo"})
_abbrev("ty", {
    "RU": "спасибо", "DE": "danke",
    "FR": "merci", "ES": "gracias"})
_abbrev("np", {
    "RU": "без проблем", "DE": "kein Problem",
    "FR": "pas de problème", "ES": "no hay problema"})
_abbrev("wp", {
    "RU": "хорошо сыграно", "DE": "gut gespielt",
    "FR": "bien joué", "ES": "bien jugado"})
_abbrev("gj", {
    "RU": "молодец", "DE": "gute Arbeit",
    "FR": "bon travail", "ES": "buen trabajo"})
_abbrev("gl", {
    "RU": "удачи", "DE": "viel Glück",
    "FR": "bonne chance", "ES": "buena suerte"})
_abbrev("hf", {
    "RU": "удачи", "DE": "viel Spaß",
    "FR": "amusez-vous", "ES": "diviértanse"})
_abbrev("omw", {
    "RU": "иду", "DE": "bin unterwegs",
    "FR": "j'arrive", "ES": "voy"})
_abbrev("oom", {
    "RU": "нет маны", "DE": "kein Mana",
    "FR": "plus de mana", "ES": "sin maná"})
_abbrev("lfg", {
    "RU": "ищу группу", "DE": "suche Gruppe",
    "FR": "cherche groupe", "ES": "busco grupo"})
_abbrev("lfm", {
    "RU": "ищу людей", "DE": "suche Mitglieder",
    "FR": "cherche joueurs", "ES": "busco miembros"})
_abbrev("inv", {
    "RU": "инвайт", "DE": "Einladung",
    "FR": "invite", "ES": "invitar"})
_abbrev("rdy", {
    "RU": "готов", "DE": "bereit",
    "FR": "prêt", "ES": "listo"})
_abbrev("inc", {
    "RU": "идут на нас", "DE": "Feind kommt",
    "FR": "ennemi arrive", "ES": "enemigo viene"})
_abbrev("wts", {
    "RU": "продам", "DE": "verkaufe",
    "FR": "vends", "ES": "vendo"})
_abbrev("wtb", {
    "RU": "куплю", "DE": "kaufe",
    "FR": "achète", "ES": "compro"})
_abbrev("mb", {
    "RU": "моя ошибка", "DE": "mein Fehler",
    "FR": "ma faute", "ES": "mi culpa"})
_abbrev("idd", {
    "RU": "инстанс", "DE": "Instanz",
    "FR": "instance", "ES": "instancia"})
_abbrev("lf", {
    "RU": "ищу", "DE": "suche",
    "FR": "cherche", "ES": "busco"})
_abbrev("pls", {
    "RU": "пожалуйста", "DE": "bitte",
    "FR": "svp", "ES": "por favor"})
_abbrev("thx", {
    "RU": "спасибо", "DE": "danke",
    "FR": "merci", "ES": "gracias"})
_abbrev("nvm", {
    "RU": "неважно", "DE": "egal",
    "FR": "pas grave", "ES": "no importa"})
_abbrev("idk", {
    "RU": "не знаю", "DE": "weiß nicht",
    "FR": "je sais pas", "ES": "no sé"})
_abbrev("imo", {
    "RU": "по-моему", "DE": "meiner Meinung nach",
    "FR": "à mon avis", "ES": "en mi opinión"})
_abbrev("tbh", {
    "RU": "честно говоря", "DE": "ehrlich gesagt",
    "FR": "honnêtement", "ES": "la verdad"})
_abbrev("btw", {
    "RU": "кстати", "DE": "übrigens",
    "FR": "au fait", "ES": "por cierto"})
_abbrev("gtg", {
    "RU": "мне пора", "DE": "muss los",
    "FR": "je dois y aller", "ES": "me tengo que ir"})
_abbrev("nw", {
    "RU": "без проблем", "DE": "kein Problem",
    "FR": "pas de souci", "ES": "no hay problema"})

# Common short words (too short for lingua or commonly auto-detected wrong)
_abbrev("yes", {
    "RU": "да", "DE": "ja", "FR": "oui", "ES": "sí"})
_abbrev("yea", {
    "RU": "да", "DE": "ja", "FR": "ouais", "ES": "sí"})
_abbrev("yeah", {
    "RU": "да", "DE": "ja", "FR": "ouais", "ES": "sí"})
_abbrev("yep", {
    "RU": "да", "DE": "jap", "FR": "ouais", "ES": "sip"})
_abbrev("no", {
    "RU": "нет", "DE": "nein", "FR": "non", "ES": "no"})
_abbrev("nope", {
    "RU": "неа", "DE": "nö", "FR": "nan", "ES": "nel"})
_abbrev("hi", {
    "RU": "привет", "DE": "hallo", "FR": "salut", "ES": "hola"})
_abbrev("sup", {
    "RU": "привет", "DE": "was geht", "FR": "salut", "ES": "qué tal"})
_abbrev("go", {
    "RU": "вперёд", "DE": "los", "FR": "go", "ES": "vamos"})

# Summon requests (WoW convention: "123" = "summon me")
_abbrev("123", {
    "RU": "саммон", "EN": "summon",
    "DE": "Beschwörung", "FR": "invocation", "ES": "invocar"})
_abbrev("123 pls", {
    "RU": "саммон пожалуйста", "EN": "summon please",
    "DE": "Beschwörung bitte", "FR": "invocation svp",
    "ES": "invocar por favor"})
_abbrev("sum pls", {
    "RU": "саммон пожалуйста", "EN": "summon please",
    "DE": "Beschwörung bitte", "FR": "invocation svp",
    "ES": "invocar por favor"})
_abbrev("sum", {
    "RU": "саммон", "EN": "summon",
    "DE": "Beschwörung", "FR": "invocation", "ES": "invocar"})
_abbrev("summ", {
    "RU": "саммон", "EN": "summon",
    "DE": "Beschwörung", "FR": "invocation", "ES": "invocar"})
_abbrev("summ pls", {
    "RU": "саммон пожалуйста", "EN": "summon please",
    "DE": "Beschwörung bitte", "FR": "invocation svp",
    "ES": "invocar por favor"})
_abbrev("summ all pls", {
    "RU": "саммон всех пожалуйста", "EN": "summon all please",
    "DE": "alle beschwören bitte", "FR": "invocation tous svp",
    "ES": "invocar a todos por favor"})
_abbrev("sum all pls", {
    "RU": "саммон всех пожалуйста", "EN": "summon all please",
    "DE": "alle beschwören bitte", "FR": "invocation tous svp",
    "ES": "invocar a todos por favor"})

# Raid / instance coordination
_abbrev("bio", {
    "RU": "перерыв", "EN": "bio break",
    "DE": "Bio-Pause", "FR": "pause bio", "ES": "pausa bio"})
_abbrev("bio break", {
    "RU": "перерыв", "EN": "bio break",
    "DE": "Bio-Pause", "FR": "pause bio", "ES": "pausa bio"})
_abbrev("sec bio", {
    "RU": "секунду, перерыв", "EN": "sec, bio break",
    "DE": "Sekunde, Bio-Pause", "FR": "seconde, pause bio",
    "ES": "segundo, pausa bio"})
_abbrev("30 sec bio", {
    "RU": "30 секунд перерыв", "EN": "30 sec bio break",
    "DE": "30 Sek Bio-Pause", "FR": "30 sec pause bio",
    "ES": "30 seg pausa bio"})
_abbrev("2 min bio", {
    "RU": "2 минуты перерыв", "EN": "2 min bio break",
    "DE": "2 Min Bio-Pause", "FR": "2 min pause bio",
    "ES": "2 min pausa bio"})
_abbrev("5 min bio", {
    "RU": "5 минут перерыв", "EN": "5 min bio break",
    "DE": "5 Min Bio-Pause", "FR": "5 min pause bio",
    "ES": "5 min pausa bio"})
_abbrev("on last", {
    "RU": "на последнем боссе", "EN": "on last boss",
    "DE": "beim letzten Boss", "FR": "au dernier boss",
    "ES": "en el último jefe"})
_abbrev("wipe", {
    "RU": "вайп", "EN": "wipe",
    "DE": "Wipe", "FR": "wipe", "ES": "wipe"})
_abbrev("lust", {
    "RU": "героизм", "EN": "bloodlust",
    "DE": "Kampfrausch", "FR": "furie sanguinaire",
    "ES": "ansia de sangre"})
_abbrev("bl", {
    "RU": "героизм", "EN": "bloodlust",
    "DE": "Kampfrausch", "FR": "furie sanguinaire",
    "ES": "ansia de sangre"})
_abbrev("hero", {
    "RU": "героизм", "EN": "heroism",
    "DE": "Heldentum", "FR": "héroïsme", "ES": "heroísmo"})
_abbrev("brez", {
    "RU": "боевой рез", "EN": "battle rez",
    "DE": "Kampfrez", "FR": "rez combat", "ES": "rez combate"})
_abbrev("rez", {
    "RU": "воскрешение", "EN": "resurrect",
    "DE": "Wiederbelebung", "FR": "résurrection", "ES": "resurrección"})
_abbrev("rezz", {
    "RU": "воскрешение", "EN": "resurrect",
    "DE": "Wiederbelebung", "FR": "résurrection", "ES": "resurrección"})
_abbrev("rezz pls", {
    "RU": "воскресите пожалуйста", "EN": "rez please",
    "DE": "Rez bitte", "FR": "rez svp", "ES": "rez por favor"})
_abbrev("rez pls", {
    "RU": "воскресите пожалуйста", "EN": "rez please",
    "DE": "Rez bitte", "FR": "rez svp", "ES": "rez por favor"})
_abbrev("cds", {
    "RU": "кулдауны", "EN": "cooldowns",
    "DE": "Abklingzeiten", "FR": "cooldowns", "ES": "cooldowns"})
_abbrev("pop cds", {
    "RU": "юзайте кулдауны", "EN": "pop cooldowns",
    "DE": "CDs nutzen", "FR": "pop les CDs", "ES": "usar CDs"})
_abbrev("kick", {
    "RU": "сбейте каст", "EN": "interrupt",
    "DE": "unterbrechen", "FR": "interrompre", "ES": "interrumpir"})
_abbrev("int", {
    "RU": "сбейте каст", "EN": "interrupt",
    "DE": "unterbrechen", "FR": "interrompre", "ES": "interrumpir"})
_abbrev("gl guys", {
    "RU": "удачи, ребята", "EN": "good luck guys",
    "DE": "viel Glück Leute", "FR": "bonne chance les gars",
    "ES": "buena suerte chicos"})
_abbrev("gl all", {
    "RU": "всем удачи", "EN": "good luck all",
    "DE": "allen viel Glück", "FR": "bonne chance à tous",
    "ES": "buena suerte a todos"})
_abbrev("gl hf", {
    "RU": "удачи, весёлой игры", "EN": "good luck, have fun",
    "DE": "viel Glück und Spaß", "FR": "bonne chance, amusez-vous",
    "ES": "buena suerte, diviértanse"})
_abbrev("gg wp", {
    "RU": "хорошая игра, молодцы", "EN": "good game, well played",
    "DE": "gutes Spiel, gut gespielt",
    "FR": "bien joué", "ES": "buen juego, bien jugado"})
_abbrev("gotta go", {
    "RU": "мне пора", "EN": "gotta go",
    "DE": "muss los", "FR": "je dois y aller",
    "ES": "me tengo que ir"})
_abbrev("zug zug", {
    "RU": "зуг зуг (да, сэр)", "EN": "zug zug (yes, sir)",
    "DE": "Zug Zug (jawohl)", "FR": "zug zug (oui chef)",
    "ES": "zug zug (sí, señor)"})
_abbrev("zamn", {
    "RU": "ого", "EN": "damn",
    "DE": "verdammt", "FR": "la vache",
    "ES": "caramba"})

# fmt: on

# ---------------------------------------------------------------------------
# Merge glossary abbreviations (Pirson's WoW Translator).
# Our entries have priority — glossary only fills gaps.
# ---------------------------------------------------------------------------
try:
    from app.glossary_data import SAFE_ABBREVIATIONS as _GLOSSARY_ABBREVS

    _glossary_added = 0
    for _key, _translations in _GLOSSARY_ABBREVS.items():
        _norm = _normalize(_key)
        for _lang, _text in _translations.items():
            _lang_upper = _lang.upper()
            if (_norm, _lang_upper) not in _ABBREVIATIONS:
                _ABBREVIATIONS[(_norm, _lang_upper)] = _text
                _glossary_added += 1
    logger.debug("Merged %d glossary abbreviations", _glossary_added)
    del _GLOSSARY_ABBREVS, _glossary_added, _key, _translations, _norm, _lang, _text, _lang_upper
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def lookup(text: str, source_lang: str, target_lang: str) -> str | None:
    """Look up a phrase in the built-in phrasebook.

    Checks language-specific phrases first, then abbreviations.
    Returns translation string if found, None on miss.
    """
    norm = _normalize(text)
    tgt = target_lang.upper()

    # 1. Language-specific phrases (exact source→target match)
    result = _ENTRIES.get((norm, source_lang.upper(), tgt))
    if result is not None:
        logger.debug(
            "Phrasebook hit: %r [%s->%s] = %r",
            text, source_lang, target_lang, result,
        )
        return result

    # 2. Universal abbreviations (language-independent)
    result = _ABBREVIATIONS.get((norm, tgt))
    if result is not None:
        logger.debug(
            "Abbreviation hit: %r [->%s] = %r",
            text, target_lang, result,
        )
        return result

    return None


def lookup_abbreviation(text: str, target_lang: str) -> str | None:
    """Look up a universal abbreviation (no source language needed).

    Use for pre-detection lookup of short gaming abbreviations
    that are identical across all languages.
    """
    result = _ABBREVIATIONS.get((_normalize(text), target_lang.upper()))
    if result is not None:
        logger.debug(
            "Abbreviation pre-detect: %r [->%s] = %r",
            text, target_lang, result,
        )
    return result


def stats() -> dict[str, int]:
    """Return phrasebook statistics."""
    sources = set()
    targets = set()
    phrases = set()
    for norm_text, src, tgt in _ENTRIES:
        sources.add(src)
        targets.add(tgt)
        phrases.add(norm_text)
    abbrev_phrases = {abbr for abbr, _ in _ABBREVIATIONS}
    abbrev_langs = {lang for _, lang in _ABBREVIATIONS}
    return {
        "entries": len(_ENTRIES) + len(_ABBREVIATIONS),
        "unique_phrases": len(phrases | abbrev_phrases),
        "languages": len(sources | targets | abbrev_langs),
    }
