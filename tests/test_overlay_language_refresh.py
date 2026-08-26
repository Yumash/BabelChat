"""A language change has to reach the windows already on screen.

Both overlays build their chrome once and a widget keeps the string it was
constructed with, so setting the interface language changed nothing already
drawn. The setting appeared to do nothing at all until the next launch, which
is indistinguishable from a broken control — and it was fixed on the GTK side
first, which left the changelog promising Windows users a repair they had not
been given.

Read from the source rather than by driving the widgets. That is weaker, and
it is written down because it is a choice: constructing `ChatOverlay` under
pytest kills the interpreter outright — no traceback, no failure, the run just
stops — which is why nothing else in this suite instantiates it either, and
`gi` is absent on Windows and on CI so the GTK half could not be built here
regardless. The behaviour was verified by hand instead, off-screen, with the
language switched under a live overlay: all five chrome labels and all
thirteen filter tabs followed, and the ON/OFF badge kept its state.

What the source can still be held to is the thing that actually rots: a label
added to the chrome and forgotten in the refresh.
"""

from __future__ import annotations

import ast
import pathlib
import re

from app.i18n import UI_LANGUAGES

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"

#: `tr("some.key")` anywhere in a source file.
TR_KEY = re.compile(r'tr\(\s*"([^"]+)"')


def source_of(module: str) -> str:
    return (APP / module).read_text(encoding="utf-8")


def method_source(module: str, name: str) -> str:
    """The text of one method, or "" when the module does not define it."""
    text = source_of(module)
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(text, node) or ""
    return ""


# ── both frontends can do it at all ──────────────────────────────────────────


def test_both_overlays_can_relabel_themselves():
    """This was fixed on GTK and not on Qt while the changelog described it as
    fixed outright. Neither half is allowed to be the only one again."""
    for module in ("overlay.py", "overlay_gtk.py"):
        assert method_source(module, "apply_language"), f"{module} cannot relabel itself"


def test_both_entry_points_call_it_when_settings_are_saved():
    """A refresh that exists and is never called is the same bug with more
    code in it."""
    for entry, overlay in (("main.py", "overlay"), ("main_gtk.py", "overlay")):
        text = source_of(entry)
        calls = {ast.get_source_segment(text, node) for node in ast.walk(ast.parse(text)) if isinstance(node, ast.Call)}

        assert f"{overlay}.apply_language()" in calls, f"{entry} never refreshes the overlay"


# ── and neither leaves a label behind ────────────────────────────────────────


def test_every_label_the_qt_chrome_builds_is_refreshed():
    """The failure mode this guards is not today's code, it is next year's: a
    label added to the toolbar and forgotten here shows up as one English
    word among Russian ones, which nobody reports as a bug."""
    built = set(TR_KEY.findall(source_of("overlay_chrome.py")))
    refreshed = method_source("overlay.py", "apply_language")

    missing = sorted(key for key in built if key not in refreshed)

    assert built, "no translated labels found — has the chrome moved?"
    assert missing == [], f"built by the chrome and never refreshed: {missing}"


def test_the_clipboard_dialog_is_refreshed_too():
    """It is a separate window, created on demand by the hotkey and then kept,
    so it outlives the setting changed after it — and being separate is exactly
    why it was missed."""
    refresh = method_source("overlay.py", "apply_language")

    assert "self._reply_dialog.apply_language()" in refresh
    assert method_source("overlay_reply.py", "apply_language"), "the dialog cannot relabel itself"


def test_the_tray_menu_is_refreshed_too():
    """The tray is the one window a user cannot close and reopen to get the new
    language — it is only ever built once, at startup."""
    text = source_of("main.py")
    calls = {
        ast.get_source_segment(text, node)
        for node in ast.walk(ast.parse(text))
        if isinstance(node, ast.Call)
    }

    assert "tray.apply_language()" in calls, "the tray menu keeps the old language"
    assert method_source("tray.py", "apply_language"), "the tray cannot relabel itself"


def test_the_qt_refresh_reaches_the_filter_tabs():
    """They are built from the shared FILTER_TABS declaration, so their keys
    are not in the chrome's source to be matched above — the bar relabels
    itself and the overlay has to ask it to."""
    assert "self._filter_bar.apply_language()" in method_source("overlay.py", "apply_language")
    assert method_source("overlay_widgets.py", "apply_language"), "the filter bar cannot relabel"


def test_the_widgets_the_qt_refresh_touches_are_kept_somewhere():
    """Two of them were locals in a builder function, so the refresh could
    name them but never reach them — an AttributeError on every settings
    save."""
    # Assigned by the chrome builder as `overlay._x`, or by the overlay itself
    # as `self._x` — the lazily created clipboard dialog is the second kind.
    assigned = set(re.findall(r"overlay\.(_\w+)\s*=", source_of("overlay_chrome.py")))
    assigned |= set(re.findall(r"self\.(_\w+)\s*=", source_of("overlay.py")))

    refresh = method_source("overlay.py", "apply_language")
    # Widgets only — those the refresh calls a method on. `_translation_enabled`
    # is read as a value, not sent a message.
    attributes = set(re.findall(r"self\.(_\w+)\.", refresh))

    assert attributes, "the refresh touches no widgets at all"
    for attribute in attributes:
        assert attribute in assigned, (
            f"apply_language calls self.{attribute}, which nothing ever assigns"
        )


def test_the_badge_is_refreshed_from_its_state_not_from_the_table_alone():
    """It is the one label whose text depends on more than the language.
    Writing the "on" string unconditionally would show a stopped translation
    as running, or the reverse — the label and the behaviour disagreeing is
    worse than the label being stale."""
    refresh = method_source("overlay.py", "apply_language")

    assert "overlay.badge.on" in refresh and "overlay.badge.off" in refresh
    assert "_translation_enabled" in refresh, "the badge is relabelled without consulting its state"


# ── the wizard offers what the app actually has ──────────────────────────────


def test_the_gtk_wizard_offers_every_language_the_app_has():
    """`_UI_LANGS` was a hand-written copy of the table. A translation added to
    UI_LANGUAGES and missed there leaves the dropdown falling back to its first
    entry, and finishing the wizard persists that over the language the locale
    guess had got right — the same silent clamp that was just removed from
    `tr.set_language`, one file over."""
    assert "_UI_LANGS = list(UI_LANGUAGES.items())" in source_of("setup_wizard_gtk.py")


def test_the_language_table_has_the_shape_that_call_produces():
    """`_dropdown` unpacks (code, label) pairs and indexes its codes list by an
    upper-case code. A table shaped any other way fails at wizard startup, on
    Linux only, where it would be found by a user rather than by this."""
    pairs = list(UI_LANGUAGES.items())

    assert len(pairs) >= 2
    for code, label in pairs:
        assert code == code.upper(), f"{code!r} is not the upper-case form the lookup uses"
        assert label and label != code, f"{code!r} has no name to show in the dropdown"


# ── the tray on Linux, and what the wizard remembers ─────────────────────────


def test_the_gtk_tray_menu_is_translated_at_all():
    """It was five English literals. The keys existed and the Qt tray had been
    using them since it was written; the GTK menu simply never went through
    `tr`, so a Russian user got a Russian overlay above an English tray."""
    text = source_of("main_gtk.py")
    items = re.findall(r"MenuItem\(\s*\"[^\"]+\"\s*,\s*([^,)]+)", text)

    assert items, "no menu items found — has the tray moved?"
    for label in items:
        assert "tr(" in label or label.strip().startswith("_"), f"hardcoded tray label: {label.strip()}"


def test_the_gtk_tray_is_refreshed_when_settings_are_saved():
    """Same reason as the Qt one: the tray is built once at startup and there
    is no reopening it, so nothing else will ever bring it into the language
    the user just picked."""
    text = source_of("main_gtk.py")
    saved = method_source("main_gtk.py", "_on_saved")

    assert saved, "the settings callback has moved"
    assert "tray.update_item" in saved, "the tray keeps the old language"
    assert 'tr("tray.settings")' in text, "the menu is refreshed with something other than the table"


def test_the_gtk_tray_overlay_item_is_written_from_state():
    """It says Hide or Show depending on where the overlay is. Relabelling it
    from the table alone would offer to hide a window that is already hidden —
    the same trap as the translation badge."""
    label = method_source("main_gtk.py", "_overlay_item_label")

    assert label, "the label is not derived anywhere"
    assert "tray.hide_overlay" in label and "tray.show_overlay" in label


def test_the_qt_wizard_keeps_what_was_typed_across_a_language_change():
    """Changing the language restarts this wizard, and the new one builds its
    fields from the config — so anything not written to the config first is
    gone: an API key pasted on page two, the WoW path browsed for on page
    three. The GTK wizard snapshots and restores; the changelog describes the
    carry-across without naming a platform."""
    handler = method_source("setup_wizard.py", "_on_ui_lang_changed")

    assert handler, "the language handler has moved"
    assert "apply_to" in handler, "the entered credentials are dropped on restart"
    assert "wow_path" in handler, "the entered WoW path is dropped on restart"
