"""Which language the interface opens in before anything has been saved.

The app defaults to Russian, which is right for the audience it was written
for and wrong for everyone else on their very first launch: the setup wizard
is the first thing a new player sees, and it was showing them Russian whatever
their machine was set to. The OS locale is the only signal available at that
point, so it decides.

The dangerous half is knowing when NOT to consult it. The wizard reopens
whenever no provider is configured — an expired key, a config migrated from
before the provider registry — and that is not a first run: a real preference
is sitting in the config file. The wizard seeds its dropdown from the language
on screen and writes it back on finish, so guessing there does not merely
mislabel a window, it overwrites the choice the user made.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from app.config import AppConfig, saved_config_exists
from app.i18n import (
    UI_LANGUAGES,
    _windows_ui_language,
    guess_ui_language,
    startup_ui_language,
)

#: Every variable the guesser reads. Cleared wholesale per test so the machine
#: running the suite cannot answer for the machine being simulated.
LOCALE_VARS = ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")


@pytest.fixture
def env(monkeypatch):
    """A machine with no locale opinion, plus a lever to give it one."""
    for var in LOCALE_VARS:
        monkeypatch.delenv(var, raising=False)
    # getlocale() reads the process's own setting, which pytest inherits from
    # whoever ran it. Neutralise it; the tests that care set it themselves.
    monkeypatch.setattr("app.i18n.locale.getlocale", lambda *a: (None, None))
    # Same for Windows: CI runs on a Windows runner whose interface is English,
    # so leaving this live would have every "no locale anywhere" test answered
    # by the runner's own machine.
    monkeypatch.setattr("app.i18n._windows_ui_language", lambda: "")
    return monkeypatch


# ── reading the environment ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("es_ES.UTF-8", "ES"),
        ("en_GB", "EN"),
        ("ru_RU.UTF-8", "RU"),
        ("es", "ES"),
        ("en_US.iso88591", "EN"),
        ("ru_RU.UTF-8@cyrillic", "RU"),
    ],
)
def test_a_locale_names_its_language(env, value, expected):
    env.setenv("LANG", value)

    assert guess_ui_language() == expected


def test_language_wins_over_the_lc_variables(env):
    """gettext resolves LANGUAGE first and LANG nearly last. Ordering them the
    other way round is the easy mistake — LANG is the famous one — and it
    silently ignores the variable the user set precisely to be obeyed."""
    env.setenv("LANGUAGE", "es")
    env.setenv("LC_ALL", "ru_RU.UTF-8")
    env.setenv("LC_MESSAGES", "ru_RU.UTF-8")
    env.setenv("LANG", "ru_RU.UTF-8")

    assert guess_ui_language() == "ES"


def test_lc_all_wins_over_lang(env):
    env.setenv("LC_ALL", "es_ES.UTF-8")
    env.setenv("LANG", "en_US.UTF-8")

    assert guess_ui_language() == "ES"


def test_language_is_a_preference_list(env):
    """LANGUAGE holds colon-separated fallbacks, unlike the others. Reading it
    as a single locale would see "de:es" as a language named "de:es"."""
    env.setenv("LANGUAGE", "de:es:ru")

    assert guess_ui_language() == "ES"


def test_an_unsupported_language_does_not_end_the_search(env):
    """A German desktop with LANG=de_DE has no German UI to offer, but its
    LC_MESSAGES may still name one this build has. Returning the default at
    the first variable that says anything would never look."""
    env.setenv("LANGUAGE", "de")
    env.setenv("LANG", "es_ES.UTF-8")

    assert guess_ui_language() == "ES"


# ── falling back ─────────────────────────────────────────────────────────────


def test_no_locale_at_all_falls_back(env):
    assert guess_ui_language() == "RU"


def test_a_language_this_build_cannot_show_falls_back(env):
    """Translating the UI is not the same as translating chat: the app speaks
    twenty languages to WoW and three to its own user."""
    env.setenv("LANG", "ja_JP.UTF-8")

    assert guess_ui_language() == "RU"


@pytest.mark.parametrize("value", ["", "C", "POSIX", "C.UTF-8"])
def test_the_uninformative_locales_say_nothing(env, value):
    env.setenv("LANG", value)

    assert guess_ui_language() == "RU"


def test_the_process_locale_answers_when_the_environment_is_silent(env):
    """Windows sets none of these variables; getlocale() is all there is."""
    env.setattr("app.i18n.locale.getlocale", lambda *a: ("es_ES", "UTF-8"))

    assert guess_ui_language() == "ES"


def test_a_malformed_locale_setting_is_not_a_crash(env):
    """getlocale() raises on a setting it cannot parse. Failing to guess a
    language must not stop the app from starting."""

    def explode(*_args):
        raise ValueError("unknown locale format")

    env.setattr("app.i18n.locale.getlocale", explode)

    assert guess_ui_language() == "RU"


def test_the_caller_chooses_the_fallback(env):
    assert guess_ui_language(default="EN") == "EN"


def test_it_only_ever_returns_a_language_the_ui_has(env):
    """The supported set is UI_LANGUAGES, not a list copied beside it — a
    fourth translation should not need this function edited to be reachable."""
    for value in ("es_ES", "en_US", "ru_RU", "zz_ZZ", "de_DE", ""):
        env.setenv("LANG", value)

        assert guess_ui_language() in UI_LANGUAGES


# ── when the guess is allowed to speak at all ────────────────────────────────


def test_a_saved_choice_is_honoured(env):
    """The ordinary case: the config file exists, so it decides."""
    env.setenv("LANG", "de_DE.UTF-8")

    assert startup_ui_language(config_exists=True, saved="ES") == "ES"


def test_the_guess_does_not_overrule_a_saved_choice(env):
    """The wizard reopens whenever no provider is configured, not only on a
    first run — an expired key does it, so does a config migrated from before
    the provider registry. Treating that as a first run consults the OS locale
    over a preference that already exists, and because the welcome page seeds
    its dropdown from the language on screen and finish() writes it back, a
    user who clicked through would find Spanish saved as German."""
    env.setenv("LANG", "de_DE.UTF-8")

    assert startup_ui_language(config_exists=True, saved="ES") != "RU"
    assert startup_ui_language(config_exists=True, saved="ES") == "ES"


def test_a_first_run_has_nothing_to_honour(env):
    """No config file: `saved` is only the dataclass default, not a choice."""
    env.setenv("LANG", "es_ES.UTF-8")

    assert startup_ui_language(config_exists=False, saved="RU") == "ES"


def test_a_first_run_on_a_machine_with_no_locale_keeps_the_default(env):
    assert startup_ui_language(config_exists=False, saved="RU") == "RU"


def test_both_entry_points_ask_the_same_question():
    """This decision lived in one frontend and not the other for a release,
    which is how Linux users ended up unable to change the interface language
    at all. Whatever it grows into, both callers get the same answer."""
    import ast

    root = pathlib.Path(__file__).resolve().parent.parent
    for entry in ("main.py", "main_gtk.py"):
        source = (root / "app" / entry).read_text(encoding="utf-8")
        tree = ast.parse(source)
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }

        assert "startup_ui_language" in called, f"{entry} decides the startup language by itself"
        assert "guess_ui_language" not in called, f"{entry} reaches past the shared rule"
        assert "saved_config_exists" in called, (
            f"{entry} decides what a first run is without asking config.py"
        )

        # os.path.exists(CONFIG_FILE) is the wrong question and was asked here
        # twice: load() also reads config.json.bak, so the main file's absence
        # is not proof there is no saved language.
        segments = [ast.get_source_segment(source, node) or "" for node in ast.walk(tree)]
        stats = [seg for seg in segments if "CONFIG_FILE" in seg and "exists" in seg]
        assert stats == [], f"{entry} still stats the config path: {stats}"


# ── Windows answers this question differently ────────────────────────────────


def test_windows_says_which_language_its_interface_is_in(env):
    """The env vars are a POSIX convention; Windows sets none of them."""
    env.setattr("app.i18n._windows_ui_language", lambda: "en_US")

    assert guess_ui_language() == "EN"


def test_the_c_runtime_locale_name_is_not_an_iso_code(env):
    """What `getlocale()` returns on Windows, measured: `('Russian_Russia',
    '1252')`. It is the C runtime's name for the locale, not a language code,
    and reading it as one is why every Windows first run answered RU whatever
    the machine was set to — including the English ones this was written for.
    A machine whose interface is English must not be talked out of it by the
    formats locale next door."""
    env.setattr("app.i18n.locale.getlocale", lambda *a: ("English_United States", "1252"))
    env.setattr("app.i18n._windows_ui_language", lambda: "en_US")

    assert guess_ui_language() == "EN"


def test_the_windows_lookup_stays_on_windows(monkeypatch):
    """It is called unconditionally, so it has to be inert everywhere else —
    `ctypes.windll` does not exist on Linux and reaching for it would raise
    during startup on the platform this app was ported to."""
    monkeypatch.setattr("app.i18n.sys.platform", "linux")

    assert _windows_ui_language() == ""


def test_an_lcid_python_has_no_name_for_says_nothing(monkeypatch):
    """`windows_locale` is a fixed table shipped with Python; a language ID
    added to Windows after that table was written is simply absent from it,
    and must read as "no answer" rather than as a crash."""
    monkeypatch.setattr("app.i18n.sys.platform", "win32")
    monkeypatch.setattr("app.i18n.locale.windows_locale", {}, raising=False)

    assert _windows_ui_language() == ""


def test_the_environment_still_outranks_windows(env):
    """A user who sets LANGUAGE on Windows — through a launcher script, say —
    is asking for something specific, and asked first."""
    env.setenv("LANGUAGE", "es")
    env.setattr("app.i18n._windows_ui_language", lambda: "en_US")

    assert guess_ui_language() == "ES"


# ── what counts as having run this app before ────────────────────────────────


def _write(path, **fields) -> None:
    path.write_text(json.dumps(fields), encoding="utf-8")


def test_a_config_only_in_the_backup_still_counts(tmp_path):
    """`AppConfig.load` reads config.json.bak when the main file is gone — and
    hands back the language saved in it. Asking `os.path.exists(CONFIG_FILE)`
    instead calls that a first run, so the guess overrides a preference that
    was successfully loaded one line earlier; on GTK the wizard opens too,
    seeds its dropdown from the guess and writes it back on finish, which
    deletes the recovered choice for good."""
    main = tmp_path / "config.json"
    _write(main.with_suffix(".json.bak"), ui_language="ES")

    assert not main.exists()
    assert saved_config_exists(str(main)) is True
    assert AppConfig.load(str(main)).ui_language == "ES"


def test_a_corrupt_config_with_no_backup_is_a_first_run(tmp_path):
    """The other direction. `load` falls back to defaults here, so the RU it
    returns is not a choice anybody made — treating the file's presence as one
    shows the wizard in Russian to someone who has never used the app."""
    main = tmp_path / "config.json"
    main.write_text("{ this is not json", encoding="utf-8")

    assert saved_config_exists(str(main)) is False
    assert AppConfig.load(str(main)).ui_language == "RU"


def test_nothing_on_disk_is_a_first_run(tmp_path):
    assert saved_config_exists(str(tmp_path / "config.json")) is False


def test_the_question_and_the_answer_read_the_same_files(tmp_path):
    """These drifted the moment they were written apart: one stats a filename,
    the other has a fallback list. They share the list now."""
    from app.config import _config_candidates

    main = tmp_path / "config.json"
    candidates = [str(p) for p in _config_candidates(str(main))]

    assert candidates == [str(main), str(main.with_suffix(".json.bak"))]

    for candidate in candidates:
        pathlib.Path(candidate).write_text(json.dumps({"ui_language": "ES"}), encoding="utf-8")
        assert saved_config_exists(str(main)) is True
        pathlib.Path(candidate).unlink()


def test_asking_does_not_rewrite_anything(tmp_path):
    """`load` runs migrations that write backups of their own. A question that
    quietly does that is not a question."""
    main = tmp_path / "config.json"
    _write(main, deepl_api_key="secret-from-before-the-registry", ui_language="ES")
    before = {p.name for p in tmp_path.iterdir()}

    assert saved_config_exists(str(main)) is True
    assert {p.name for p in tmp_path.iterdir()} == before


@pytest.mark.parametrize(
    ("config_exists", "expected"),
    [(True, "ES"), (False, "RU")],
)
def test_the_startup_rule_takes_that_answer(env, config_exists, expected):
    """Joining the two halves: a recovered config keeps its language, a machine
    with no config at all gets the guess (RU here, the environment is bare)."""
    assert startup_ui_language(config_exists=config_exists, saved="ES") == expected


# ── the two halves agree on which languages exist ────────────────────────────


def test_setting_a_language_accepts_every_language_the_guess_can_return():
    """These were two lists: `tr.set_language` validated against a tuple while
    the guess resolved against UI_LANGUAGES. A fourth translation added to the
    table and not the tuple would be found by the guess and then silently
    clamped back to Russian on the way in — the first-run bug again, wearing a
    new hat, and silent because set_language reports nothing."""
    from app.i18n import tr

    previous = tr.get_language()
    try:
        for code in UI_LANGUAGES:
            tr.set_language(code)

            assert tr.get_language() == code, f"{code} is offered but not accepted"
    finally:
        tr.set_language(previous)


def test_a_language_that_does_not_exist_is_still_refused():
    """Widening the check must not turn it off: the fallback is what keeps a
    stale config or a hand-edited one from blanking the interface."""
    from app.i18n import tr

    previous = tr.get_language()
    try:
        tr.set_language("ZZ")

        assert tr.get_language() == "RU"
    finally:
        tr.set_language(previous)
