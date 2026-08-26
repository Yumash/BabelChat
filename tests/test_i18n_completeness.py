"""The string table: complete, reachable, and actually used.

Three failure modes, all of which shipped. A key defined in English but not in
Russian shows English inside a Russian interface. A key that no longer exists
renders as its own name — `tr` returns the key on a miss, so `settings_tab_general`
appears on screen looking almost like a label. And a string written straight
into a widget never reaches the table at all, which is how the settings dialog
ended up half in English.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.i18n import _STRINGS, tr

LANGUAGES = ("EN", "RU", "ES")
APP = Path(__file__).resolve().parent.parent / "app"

# The Qt surfaces a Russian-speaking player actually reads.
LOCALISED_MODULES = (
    "settings_dialog.py",
    "setup_wizard.py",
    "provider_settings_qt.py",
    "wizard_pages_qt.py",
    "about_tab_qt.py",
    # The GTK frontend was left out of this list, and stayed half English for
    # it: Russian checkboxes under English headings. It cannot be built here
    # (gi is not installed on the Windows dev box or on CI), so the source scan
    # is the only check it gets — which is the reason to keep it honest.
    "settings_gtk.py",
    "setup_wizard_gtk.py",
)


def source(name: str) -> str:
    return (APP / name).read_text(encoding="utf-8")


# ── completeness ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_key_exists_in_every_language(language):
    missing = sorted(key for key, values in _STRINGS.items() if language not in values)
    assert missing == [], f"{language} is missing: {missing}"


@pytest.mark.parametrize("language", LANGUAGES)
def test_no_translation_is_blank(language):
    blank = sorted(key for key, values in _STRINGS.items() if not values.get(language, "").strip())
    assert blank == [], f"{language} has empty strings: {blank}"


def test_a_placeholder_is_present_in_every_language_that_has_the_key():
    """A format field dropped from one translation raises when that language is
    selected, and only then — the kind of bug that ships to one audience."""
    mismatched = []
    for key, values in _STRINGS.items():
        fields = {lang: set(re.findall(r"\{(\w+)\}", text)) for lang, text in values.items()}
        reference = fields.get("EN", set())
        for lang, found in fields.items():
            if found != reference:
                mismatched.append((key, lang, sorted(reference), sorted(found)))
    assert mismatched == [], f"placeholders differ between languages: {mismatched}"


# ── reachability ─────────────────────────────────────────────────────────────


def referenced_keys() -> set[str]:
    keys: set[str] = set()
    for path in APP.rglob("*.py"):
        # i18n.py defines tr; its docstrings show `tr("key")` as an example.
        if path.name == "i18n.py":
            continue
        keys.update(re.findall(r'tr\(\s*"([a-z0-9_.]+)"', path.read_text(encoding="utf-8")))
    return keys


def test_every_key_the_code_asks_for_exists():
    """`tr` returns the key itself on a miss, so a typo reaches the screen as a
    plausible-looking label rather than as an error."""
    unknown = sorted(referenced_keys() - set(_STRINGS))
    assert unknown == [], f"asked for but not defined: {unknown}"


def test_a_missing_key_is_visible_rather_than_silent():
    """Pinning the current behaviour: it returns the key. That is survivable
    only because the test above exists."""
    assert tr("no.such.key.exists") == "no.such.key.exists"


def test_a_string_with_a_placeholder_renders():
    assert "7" in tr("settings.privacy.cleared", n=7)


def test_a_missing_placeholder_argument_does_not_crash_the_interface():
    """A caller that forgets an argument should lose the substitution, not the
    window."""
    rendered = tr("settings.privacy.cleared")
    assert isinstance(rendered, str) and rendered


# ── strings that never reached the table ─────────────────────────────────────

# Text that is not language: a brand name, a URL, a placeholder shown as an
# example, or styling. Anything else in a widget constructor is a missed string.
_NOT_LANGUAGE = re.compile(
    r"^(?:"
    r"\s*|[\W\d_]+|"  # punctuation, digits, symbols, icons
    r"(?:\{[^}]*\}|[^A-Za-z]|[A-Za-z]?%)+|"  # f-string composition, not copy
    r"https?://\S+|"  # links
    r"[A-Za-z-]+\.(?:py|json|log|pem|ico|png|exe)|"  # filenames
    r"[A-Za-z]:[/\\].*|"  # example paths shown as placeholders
    r"(?:Ctrl|Alt|Shift|Win)[+]\S+|"  # hotkey combinations
    r"[#][0-9a-fA-F]{3,8}|"  # colour codes
    r"WoW:.*|"  # the connection badge: a brand name and a symbol
    r"(?:Enter|Esc|Tab|Space)|"  # key names, which WoW does not translate
    r"(?:xx?-)?(?:small|medium|large)|"  # Pango size keywords
    r"\S*[/]World of Warcraft\S*|"  # the path shown as an example
    r"(?:BTC|TON|USDT(?: TRC20)?)[:]?|"  # currency tickers on the About tab
    r"GitHub[:] \S+|"  # a repository path
    r"(?:Andrey Yumashev|Pirson|WoW Translator|Buy Me a Coffee[^|]*)|"  # names and projects
    r"[A-Za-z0-9_+/=:-]{20,}|"  # opaque tokens: wallet addresses, key examples
    r"(?:DeepL|GigaChat|MyMemory|Microsoft Translator|BabelChat|WoW|Azure|Sber)"
    r"(?: [0-9]+(?:[.][0-9]+)*)?"  # ...optionally with a version number
    r")$"
)

# A string literal handed to something that draws it. The negative lookbehind
# matters: every one of these calls is *supposed* to receive tr("some.key"), and
# without it the key itself reads as hardcoded copy.
_WIDGET_TEXT = re.compile(
    r"(?:QCheckBox|QLabel|QPushButton|QGroupBox"
    r"|Gtk\.CheckButton|Gtk\.Label|Gtk\.Button|Gtk\.Expander|Gtk\.FileDialog"
    r"|setText|setToolTip|setPlaceholderText|addItem"
    # The GTK wizard builds every string through these, and leaving them out is
    # why it stayed entirely in English while the test was green.
    r"|set_label|set_markup|set_placeholder_text"
    r"|set_title|_section|_combo_row|_color_row|_scale_row|key_row|_title|_body)"
    # Either quote. The GTK modules use single quotes for anything containing
    # Pango markup, which is most of their status messages — reading only
    # double-quoted literals left every one of them invisible.
    r"\((?:[^()]{0,40}?)(?<!tr\()(['\"])((?:(?!\1).){4,}?)\1"
)


def _only_the_words(text: str) -> str:
    """What is left of a literal once composition is removed.

    An f-string is a template, not copy: `BabelChat {VERSION}` and
    `{tr('about.developer')} <b>Andrey Yumashev</b>` are assembling translated
    pieces and proper nouns, and reading them whole reports the whole template
    as untranslated English.
    """
    # The scan reads source, so "→" is six characters here — three of them
    # letters. Left in, an arrow glyph reads as untranslated English.
    # A literal backslash, escaped for the pattern: bare "\u" is read by re as
    # the start of a unicode escape and rejected for want of four hex digits.
    backslash = re.escape(chr(92))
    without_escapes = re.sub(backslash + r"(?:u[0-9a-fA-F]{4}|[nrt])", " ", text)
    without_fields = re.sub(r"\{[^{}]*\}", " ", without_escapes)
    without_markup = re.sub(r"<[^>]*>", " ", without_fields)
    # A literal split across source lines can end mid-tag; what is left is
    # an attribute list, not a sentence.
    without_markup = re.sub(r"<[^>]*$", " ", without_markup)
    return without_markup.strip()


@pytest.mark.parametrize("module", LOCALISED_MODULES)
def test_no_user_facing_string_is_written_straight_into_a_widget(module):
    """Seven of these shipped in the settings dialog — "Priority:", "Get key",
    "(other acts as fallback)" — and produced an interface half in English for
    every Russian-speaking user.

    A source scan only catches the literal-in-a-constructor shape. The test
    below walks the built interface, which is what actually reaches the user.
    """
    hardcoded = [
        text for _quote, text in _WIDGET_TEXT.findall(source(module)) if not _NOT_LANGUAGE.match(_only_the_words(text))
    ]
    assert hardcoded == [], f"{module} writes these past i18n: {hardcoded}"


# ── what the built interface actually says ───────────────────────────────────


def _russian_vocabulary() -> set[str]:
    """Every string the table can render in Russian, including substitutions."""
    rendered = set()
    for values in _STRINGS.values():
        text = values.get("RU", "")
        if not text:
            continue
        rendered.add(text)
        # A string with a placeholder reaches the screen already substituted, so
        # compare against its prefix rather than the template.
        head = re.split(r"\{\w+\}", text)[0].strip()
        if len(head) >= 4:
            rendered.add(head)
    return rendered


def _visible_texts(widget) -> list[str]:
    from PyQt6.QtWidgets import QWidget

    found = []
    for child in widget.findChildren(QWidget):
        for getter in ("text", "placeholderText", "title", "toolTip"):
            method = getattr(child, getter, None)
            if method is None:
                continue
            try:
                value = method()
            except TypeError:
                continue
            if isinstance(value, str) and value.strip():
                found.append(value.strip())
    return found


def _phrases(text: str) -> list[str]:
    """A rich-text label is several labels: `<b>Перевод:</b> MyMemory` holds a
    translated one and a brand name, and reading it whole hides either."""
    return [part.strip() for part in _strip_markup(text).split("  ") if part.strip()]


def _strip_markup(text: str) -> str:
    """Qt labels carry rich text, and exempting anything starting with a tag let
    `<b>Translation:</b> …` through — the one hardcoded English label on the
    wizard's final screen."""
    return re.sub(r"<[^>]+>", " ", text)


def _is_untranslated(text: str, vocabulary: set[str]) -> bool:
    text = _strip_markup(text).strip()
    if not text or _NOT_LANGUAGE.match(text):
        return False
    if text in vocabulary or any(text.startswith(known[:20]) for known in vocabulary if len(known) >= 20):
        return False
    # Cyrillic that is not in the table is still Russian — a provider display
    # name, a language name. It is English text that betrays a missed string.
    return not re.search(r"[А-Яа-яЁё]", text)


@pytest.mark.parametrize("dialog_name", ["settings", "wizard"])
def test_the_built_russian_interface_says_nothing_in_english(dialog_name, monkeypatch):
    """The regression this branch shipped twice: copy declared as an i18n key
    and then rendered without translating it, so `provider.deepl.key` appeared
    on screen as a field label. A source scan cannot see that — the key IS a
    string constant in the provider file, correctly.

    So build the real dialog in Russian and read what it says.
    """
    pytest.importorskip("PyQt6", reason="the Qt frontend is what this checks")
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication

    from app.config import AppConfig

    monkeypatch.setattr(tr, "_lang", "RU")

    app = QApplication.instance() or QApplication([])
    assert app is not None

    config = AppConfig(wow_path="")
    if dialog_name == "settings":
        from app.settings_dialog import SettingsDialog

        widget = SettingsDialog(config)
    else:
        from app.setup_wizard import SetupWizard

        widget = SetupWizard(config)

    vocabulary = _russian_vocabulary()
    english = sorted(
        {phrase for text in _visible_texts(widget) for phrase in _phrases(text) if _is_untranslated(phrase, vocabulary)}
    )
    widget.deleteLater()

    assert english == [], f"the Russian {dialog_name} shows: {english}"


def test_no_provider_copy_reaches_the_screen_as_its_own_key():
    """`tr` returns the key on a miss and the GTK frontend never called `tr` at
    all, so a Russian player saw the literal text `provider.deepl.key` where the
    field label belongs. Rendering now lives on the spec; this holds it there.
    """
    from app.translators import all_providers

    for language in LANGUAGES:
        tr.set_language(language)
        for spec in all_providers():
            rendered = [spec.note_text()]
            for field in spec.fields:
                rendered += [field.label_text(), field.placeholder_text(), field.help_text()]
            leaked = [text for text in rendered if text.startswith("provider.")]
            assert leaked == [], f"{spec.id} in {language} shows raw keys: {leaked}"
    tr.set_language("RU")


def test_provider_notes_and_labels_go_through_the_table():
    """A provider declares its own copy, and that copy is shown to the user. If
    it bypasses the table, adding a provider adds English to a Russian screen."""
    from app.translators import all_providers

    untranslated = []
    for spec in all_providers():
        for text in (spec.note, *(f.label for f in spec.fields)):
            if text and text not in _STRINGS and not _is_translated_value(text):
                untranslated.append((spec.id, text[:50]))
    assert untranslated == [], f"provider copy not in the string table: {untranslated}"


def _is_translated_value(text: str) -> bool:
    """True if the text is a rendered value of some key in the table."""
    return any(text in values.values() for values in _STRINGS.values())


# ── the language has to be applied, not just chosen ──────────────────────────


@pytest.mark.parametrize("entry_point", ["app/main.py", "app/main_gtk.py"])
def test_every_entry_point_applies_the_configured_ui_language(entry_point):
    """The Qt entry point had always done this and the GTK one never did, so
    every Linux user got the default interface language whatever they picked —
    and the default is Russian. Nothing failed; the setting simply had no
    effect, which is the hardest kind of bug to report.

    `gi` is not installed on Windows or on CI, so `main_gtk` cannot be imported
    here. The call is asserted in the source instead — a weaker check than
    running it, and the reason it is written down.

    Read as whole statements rather than as lines: the argument is now long
    enough to wrap, and a line scan would report an entry point that does this
    correctly as one that never does it at all.
    """
    import ast

    text = (APP.parent / entry_point).read_text(encoding="utf-8")
    tree = ast.parse(text)

    calls = [
        ast.get_source_segment(text, node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "set_language"
    ]

    assert calls, f"{entry_point} never applies the configured language"
    assert any("ui_language" in call for call in calls), calls


@pytest.mark.parametrize("module", ["app/settings_dialog.py", "app/settings_gtk.py"])
def test_changing_the_language_in_settings_takes_effect(module):
    """Saving a language that does not take hold reads as the setting being
    broken, which is what the GTK dialog did."""
    text = (APP.parent / module).read_text(encoding="utf-8")

    assert "tr.set_language(" in text, f"{module} saves the language without applying it"


def test_only_the_languages_that_exist_are_offered_as_the_interface_language():
    """Offering eleven when three are translated is a control that silently does
    nothing: anything outside them falls back to Russian inside `tr`."""
    from app.i18n import UI_LANGUAGES

    text = (APP / "settings_gtk.py").read_text(encoding="utf-8")

    assert "_UI_LANGS = list(UI_LANGUAGES)" in text, "the GTK dialog keeps its own list"
    assert set(UI_LANGUAGES) == {"RU", "EN", "ES"}


def test_both_frontends_offer_the_same_translation_languages():
    """The GTK dialog carried eleven bare codes against the Qt dialog's
    twenty-two names, so a Linux user could not pick most of the languages the
    app supports."""
    from app.languages import LANGUAGES as SHARED

    for module in ("settings_dialog.py", "settings_gtk.py"):
        text = source(module)
        assert "from app.languages import LANGUAGES" in text, f"{module} does not use the shared list"

    assert len(SHARED) >= 20
    assert SHARED["RU"] == "Русский", "languages are named in themselves"


@pytest.mark.parametrize("module", ["overlay.py", "overlay_gtk.py"])
def test_the_overlay_takes_its_words_from_the_table(module):
    """The GTK overlay never imported the string table at all, so every word on
    the surface a Linux player actually looks at was English — the filter tabs,
    the reply box, the tooltips, the "translating…" flash.

    The remaining literals are symbols and the product name, which are the same
    in every language."""
    text = source(module)

    assert "from app.i18n import tr" in text, f"{module} does not use the string table"

    literals = [
        found for _quote, found in _WIDGET_TEXT.findall(text) if not _NOT_LANGUAGE.match(_only_the_words(found))
    ]

    assert literals == [], f"{module} draws these without translating them: {literals}"


def test_both_overlays_draw_the_same_filter_tabs():
    """Each had its own hand-written list. The Qt one never grew Custom or
    Emote, so messages from either appeared under no tab but All; the GTK one
    said "LFG" where the channel is LookingForGroup, so that tab matched
    nothing at all."""
    from app.config import FILTER_TABS

    names = [name for name, _key in FILTER_TABS]

    assert names[0] == "All"
    assert "Custom" in names and "Emote" in names
    assert "LookingForGroup" in names and "LFG" not in names
    assert len(names) == len(set(names)), f"a tab is listed twice: {names}"

    # The Qt filter bar lives in overlay_widgets.py since the overlay was split.
    for module in ("overlay_widgets.py", "overlay_gtk.py"):
        assert "FILTER_TABS" in source(module), f"{module} keeps its own list"


# ── the table lives one file per language ────────────────────────────────────


def test_the_string_table_is_assembled_from_one_file_per_language():
    """It was a thousand-line literal in the middle of the module that renders
    it, so a translator had to find their language three lines at a time and a
    missing key was a hole in the middle of a table rather than a diff."""
    from app.locales import LANGUAGE_MODULES

    assert set(LANGUAGE_MODULES) == set(LANGUAGES)
    for language, module in LANGUAGE_MODULES.items():
        assert module.STRINGS, f"{language} has no strings"
        assert all(isinstance(text, str) for text in module.STRINGS.values())


def test_every_language_file_carries_the_same_keys():
    """This is what the split buys: which keys a language is missing is a set
    difference between two files."""
    from app.locales import LANGUAGE_MODULES

    reference = set(LANGUAGE_MODULES["EN"].STRINGS)
    for language, module in LANGUAGE_MODULES.items():
        missing = sorted(reference - set(module.STRINGS))
        extra = sorted(set(module.STRINGS) - reference)
        assert missing == [], f"{language} is missing: {missing}"
        assert extra == [], f"{language} has keys English does not: {extra}"


def test_i18n_holds_the_mechanism_and_not_the_translations():
    """The point of the move. If the table drifts back into this module the
    file grows past the size cap again and the locale directory becomes a
    second copy."""
    text = source("i18n.py")

    assert "from app import locales" in text
    assert text.count('": "') < 5, "translations are being written into i18n.py again"
