"""Internationalization — RU/EN/ES UI translations."""

from __future__ import annotations

import locale
import os
import sys
from typing import ClassVar

from app import locales

# All translatable strings keyed by ID
#: Key to language to text, assembled from app/locales — one module per
#: language. It used to be a thousand-line literal here, which meant every
#: translation lived in the middle of the mechanism that renders it, and a
#: translator had to find their language three lines at a time.
#:
#: The shape is unchanged, so everything that reads it still does.
_STRINGS: dict[str, dict[str, str]] = locales.STRINGS

UI_LANGUAGES = {"RU": "Русский", "EN": "English", "ES": "Español"}


class tr:
    """Simple translation helper. Call tr("key") to get localized string."""

    _lang: ClassVar[str] = "RU"

    @classmethod
    def set_language(cls, lang: str) -> None:
        # Against UI_LANGUAGES, not a tuple repeating it: a fourth translation
        # added to the table but not here would be resolved by the locale guess
        # and then silently clamped back to Russian on the way in, which is the
        # first-run bug this module exists to prevent, wearing a new hat.
        cls._lang = lang if lang in UI_LANGUAGES else "RU"

    @classmethod
    def get_language(cls) -> str:
        return cls._lang

    @classmethod
    def __class_getitem__(cls, key: str) -> str:
        """Allow tr["key"] syntax."""
        return cls(key)

    def __new__(cls, key: str, **kwargs: object) -> str:  # type: ignore[misc]
        entry = _STRINGS.get(key)
        if not entry:
            return key
        text = entry.get(cls._lang, entry.get("EN", key))
        if kwargs:
            text = text.format(**kwargs)
        return text


#: Environment variables that state the user's preferred UI language, in the
#: order gettext resolves them: LANGUAGE wins outright, and only then do the
#: LC_* variables and LANG get a say. Getting this order wrong is easy — LANG
#: is the famous one — and it silently ignores whatever LANGUAGE asked for.
_LOCALE_ENV_VARS = ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")


def _codes_in(value: str) -> list[str]:
    """Language codes named by one locale environment variable.

    LANGUAGE holds a colon-separated preference list ("es:ru"); the others hold
    a single locale ("es_ES.UTF-8"). Both reduce to the leading language part,
    upper-cased, which is what UI_LANGUAGES is keyed by.
    """
    codes = []
    for item in value.split(":"):
        code = item.split(".")[0].split("@")[0].split("_")[0].strip().upper()
        if code:
            codes.append(code)
    return codes


def _windows_ui_language() -> str:
    """The display language Windows itself is set to, as an ISO locale name.

    `locale.getlocale()` cannot answer this on Windows: it reports the C
    runtime's name for the locale — "Russian_Russia", "English_United States" —
    which is not an ISO code and which nothing here can key on. Measured on a
    Russian Windows 11: `getlocale()` gives `('Russian_Russia', '1252')`, so
    every guess fell through to the default and the first-run language was
    Russian for the whole world, which is the bug this was written to fix.

    Windows also separates the language the interface is in from the locale
    dates and numbers are formatted by — a machine can be English with Russian
    formats — and it is the first of those we are trying to match. That is
    `GetUserDefaultUILanguage`, not the format locale `getdefaultlocale` reads
    (and which is deprecated for removal besides).
    """
    if sys.platform != "win32":
        return ""
    try:
        import ctypes

        lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    except (AttributeError, OSError, ValueError):  # not the Windows we expected
        return ""
    return getattr(locale, "windows_locale", {}).get(lcid, "")


def guess_ui_language(default: str = "RU") -> str:
    """The UI language to open with when nothing has been saved yet.

    First run has no preference to honour, and defaulting to Russian for
    everyone meant a first-time player anywhere else read the setup wizard in a
    language they may not have. The OS locale is the only signal available, so
    it decides — falling back to `default` when it is absent, unreadable, or
    names a language this build has no UI for.

    Only for a genuine first run: once a config file exists it carries a real
    choice, and guessing over that replaces it with the machine's opinion.
    """
    for env_var in _LOCALE_ENV_VARS:
        for code in _codes_in(os.environ.get(env_var, "")):
            if code in UI_LANGUAGES:
                return code

    # Windows sets none of those variables, and its C-runtime locale name is
    # not something `_codes_in` can read. Ask Win32 directly before falling
    # back to the POSIX path below.
    for code in _codes_in(_windows_ui_language()):
        if code in UI_LANGUAGES:
            return code

    try:
        loc = locale.getlocale()[0] or ""
    except (ValueError, TypeError):  # a malformed locale setting, not our problem
        return default
    for code in _codes_in(loc):
        if code in UI_LANGUAGES:
            return code
    return default


def startup_ui_language(*, config_exists: bool, saved: str) -> str:
    """The language to render in before the user has had a chance to say.

    One rule, called by both entry points, because this is exactly the kind of
    decision that has drifted between the Qt and GTK frontends every time it
    was written twice: a saved choice is honoured, and only a machine that has
    never run the app is asked what language it speaks.

    `config_exists` is deliberately about the FILE, not about whether the app
    is fully set up. The setup wizard also reopens when a provider stops being
    configured, and treating that as a first run would let the OS locale
    overwrite the language the user picked the last time round.
    """
    return saved if config_exists else guess_ui_language()
