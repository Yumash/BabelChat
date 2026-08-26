"""GTK4 first-run setup wizard for BabelChat (Linux frontend).

Mirrors the PyQt SetupWizard: Welcome → API keys → WoW path → Languages →
Ready. Runs as its OWN Gtk.Application main loop before normal startup
(sequential GTK loops in one process are fine), so the overlay/main wiring
stays untouched.

Usage (from main_gtk):
    cfg = run_setup_wizard(config)
    if cfg is None:   # user cancelled/closed
        return 0
"""

from __future__ import annotations

import contextlib
import threading  # noqa: E402

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

from app.config import AppConfig, detect_wow_path  # noqa: E402
from app.i18n import UI_LANGUAGES, tr  # noqa: E402
from app.translators import all_providers  # noqa: E402
from app.translators import get as provider_get  # noqa: E402

_LANGS = [
    ("EN", "English"),
    ("RU", "Русский"),
    ("ES", "Español"),
    ("DE", "Deutsch"),
    ("FR", "Français"),
    ("PT", "Português"),
    ("IT", "Italiano"),
    ("PL", "Polski"),
    ("ZH", "中文"),
    ("KO", "한국어"),
    ("JA", "日本語"),
]
#: From the one table, not a fourth copy of it: a translation added there and
#: missed here would leave the dropdown falling back to its first entry, and
#: _finish would persist that over the language the guess had got right.
_UI_LANGS = list(UI_LANGUAGES.items())


class _WizardWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, config: AppConfig, result: dict) -> None:
        super().__init__(application=app, title=tr("wizard.title"))
        self._config = config
        self._result = result  # {"config": AppConfig|None}
        self.set_default_size(520, 480)

        self._stack = Gtk.Stack()
        self._stack.set_vexpand(True)
        self._pages: list[Gtk.Widget] = []
        self._build_pages()
        self._index = 0

        # Nav bar
        self._back = Gtk.Button(label=tr("wizard.back"))
        self._back.connect("clicked", lambda _b: self._go(-1))
        self._next = Gtk.Button(label=tr("wizard.next"))
        self._next.add_css_class("suggested-action")
        self._next.connect("clicked", self._on_next)
        self._step_lbl = Gtk.Label()
        self._step_lbl.set_hexpand(True)
        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        nav.set_margin_top(8)
        nav.append(self._back)
        nav.append(self._step_lbl)
        nav.append(self._next)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for m in ("set_margin_top", "set_margin_bottom", "set_margin_start", "set_margin_end"):
            getattr(root, m)(16)
        root.append(self._stack)
        root.append(nav)
        self.set_child(root)
        self._sync_nav()

    # ── page (re)building ────────────────────────────────────────────────
    def _build_pages(self) -> None:
        """(Re)build all pages from scratch so tr() text reflects the current
        language. Called on init and again whenever the interface-language
        dropdown changes, so the wizard updates live rather than only on the
        NEXT run."""
        snapshot = self._snapshot_fields() if self._pages else None

        for page in self._pages:
            self._stack.remove(page)
        self._pages = []

        for builder in (self._page_welcome, self._page_api, self._page_wow,
                        self._page_langs, self._page_ready):
            page = builder()
            self._pages.append(page)
            self._stack.add_child(page)

        if snapshot is not None:
            self._restore_fields(snapshot)
            self._stack.set_visible_child(self._pages[self._index])

    def _snapshot_fields(self) -> dict:
        """Capture whatever the user has already entered, so switching the
        interface language mid-wizard (a rebuild) doesn't lose it."""
        snap: dict = {
            "ui_lang": self._dd_code(self._ui_lang),
            "priority": self._dd_code(self._priority),
            "wow_path": self._wow_entry.get_text(),
            "own_lang": self._dd_code(self._own_lang),
            "target_lang": self._dd_code(self._target_lang),
            "providers": {
                pid: {key: entry.get_text() for key, entry in fields.items()}
                for pid, fields in self._provider_entries.items()
            },
        }
        return snap

    def _restore_fields(self, snap: dict) -> None:
        self._set_dd_code(self._ui_lang, snap["ui_lang"])
        self._set_dd_code(self._priority, snap["priority"])
        self._wow_entry.set_text(snap["wow_path"])
        self._set_dd_code(self._own_lang, snap["own_lang"])
        self._set_dd_code(self._target_lang, snap["target_lang"])
        for pid, values in snap["providers"].items():
            fields = self._provider_entries.get(pid, {})
            for key, text in values.items():
                entry = fields.get(key)
                if entry is not None:
                    entry.set_text(text)

    @staticmethod
    def _set_dd_code(dd: Gtk.DropDown, code: str) -> None:
        codes = getattr(dd, "_codes", [])
        with contextlib.suppress(ValueError):
            dd.set_selected(codes.index(code))

    def _on_ui_lang_changed(self, dd: Gtk.DropDown, _param: object) -> None:
        code = self._dd_code(dd)
        if code == tr.get_language():
            return
        tr.set_language(code)
        self._config.ui_language = code
        # Rebuild so every page (including this one) re-renders in the new
        # language immediately, instead of only taking effect next launch.
        self._build_pages()
        self._sync_nav()
        self.set_title(tr("wizard.title"))

    # ── navigation ────────────────────────────────────────────────────────
    def _go(self, delta: int) -> None:
        self._index = max(0, min(len(self._pages) - 1, self._index + delta))
        self._stack.set_visible_child(self._pages[self._index])
        self._sync_nav()

    def _sync_nav(self) -> None:
        last = self._index == len(self._pages) - 1
        self._back.set_sensitive(self._index > 0)
        self._back.set_label(tr("wizard.back"))
        self._next.set_label(tr("wizard.start") if last else tr("wizard.next"))
        # Same step names the Qt wizard uses, from the one string that holds
        # them; the key wants a name as well as the numbers.
        names = tr("wizard.steps").split("|")
        name = names[self._index] if self._index < len(names) else ""
        step = tr("wizard.step_of", current=self._index + 1, total=len(self._pages), name=name)
        self._step_lbl.set_markup(
            f'<span foreground="#888">{GLib.markup_escape_text(step)}</span>'
        )
        if last:
            self._refresh_summary()

    def _on_next(self, _btn: Gtk.Button) -> None:
        if self._index == len(self._pages) - 1:
            self._finish()
            return
        self._go(+1)

    # ── pages ─────────────────────────────────────────────────────────────
    @staticmethod
    def _title(text: str) -> Gtk.Label:
        lbl = Gtk.Label()
        lbl.set_markup(f'<span size="x-large" weight="bold">{text}</span>')
        lbl.set_xalign(0.0)
        return lbl

    @staticmethod
    def _body(text: str) -> Gtk.Label:
        lbl = Gtk.Label(label=text)
        lbl.set_wrap(True)
        lbl.set_xalign(0.0)
        return lbl

    def _dropdown(self, pairs: list[tuple[str, str]], selected_code: str) -> Gtk.DropDown:
        model = Gtk.StringList()
        for code, name in pairs:
            model.append(f"{name} ({code})")
        dd = Gtk.DropDown(model=model)
        dd._codes = [c for c, _ in pairs]
        try:
            dd.set_selected(dd._codes.index(selected_code))
        except ValueError:
            dd.set_selected(0)
        return dd

    @staticmethod
    def _dd_code(dd: Gtk.DropDown) -> str:
        return dd._codes[dd.get_selected()]

    def _page_welcome(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.append(self._title(tr("wizard.welcome.title")))
        box.append(
            self._body(tr("wizard.welcome.desc"))

        )
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.append(self._body(tr("wizard.welcome.ui_lang")))
        # Source the selection from tr (what's actually on screen right now),
        # not self._config.ui_language directly — before anything is saved,
        # config.ui_language is just its raw default and can disagree with
        # the language the page text is actually rendered in (e.g. the
        # locale-guessed language on first open), showing a dropdown value
        # that doesn't match what the user is looking at.
        self._ui_lang = self._dropdown(_UI_LANGS, tr.get_language())
        self._ui_lang.connect("notify::selected", self._on_ui_lang_changed)
        row.append(self._ui_lang)
        box.append(row)
        return box

    def _page_api(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.append(self._title(tr("wizard.api.title")))
        box.append(
            self._body(tr("wizard.api.explain"))
        )

        def key_row(label: str, value: str, validate_cb, secret: bool = True) -> tuple[Gtk.Entry, Gtk.Button]:
            r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            lbl = Gtk.Label(label=label)
            lbl.set_width_chars(14)
            lbl.set_xalign(0.0)
            entry = Gtk.Entry()
            entry.set_text(value or "")
            # Only credentials are masked. A region or an endpoint is not a
            # secret, and hiding it just makes it harder to check for typos.
            entry.set_visibility(not secret)
            entry.set_hexpand(True)
            btn = Gtk.Button(label=tr("wizard.api.validate"))
            btn.connect("clicked", validate_cb)
            r.append(lbl)
            r.append(entry)
            r.append(btn)
            box.append(r)
            return entry, btn

        # One row per credential each registered provider declares. Nothing here
        # names a provider, so adding one shows up in the wizard by itself.
        saved = self._config.providers or {}
        self._provider_entries: dict[str, dict[str, Gtk.Entry]] = {}
        for spec in all_providers():
            values = saved.get(spec.id, {})
            fields: dict[str, Gtk.Entry] = {}
            for index, pfield in enumerate(spec.fields):
                label = spec.display_name if index == 0 else pfield.label_text()
                entry, _btn = key_row(
                    label,
                    values.get(pfield.key, ""),
                    lambda _b, pid=spec.id: self._validate_provider(_b, pid),
                    secret=pfield.secret,
                )
                fields[pfield.key] = entry
            self._provider_entries[spec.id] = fields

        prio_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        prio_lbl = Gtk.Label(label=tr("settings.api.preferred"))
        prio_lbl.set_width_chars(14)
        prio_lbl.set_xalign(0.0)
        self._priority = self._dropdown(
            [(spec.id, spec.display_name) for spec in all_providers()], self._config.translator_priority or ""
        )
        prio_row.append(prio_lbl)
        prio_row.append(self._priority)
        box.append(prio_row)

        self._api_status = Gtk.Label(label="")
        self._api_status.set_xalign(0.0)
        self._api_status.set_wrap(True)
        box.append(self._api_status)
        return box

    def _page_wow(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.append(self._title(tr("wizard.wow.title")))
        box.append(
            self._body(tr("wizard.wow.explain"))
        )
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._wow_entry = Gtk.Entry()
        self._wow_entry.set_text(self._config.wow_path or "")
        self._wow_entry.set_placeholder_text("…/World of Warcraft")
        self._wow_entry.set_hexpand(True)
        detect_btn = Gtk.Button(label=tr("wizard.wow.auto"))
        detect_btn.connect("clicked", self._auto_detect)
        browse_btn = Gtk.Button(label=tr("wizard.wow.browse"))
        browse_btn.connect("clicked", self._browse)
        row.append(self._wow_entry)
        row.append(detect_btn)
        row.append(browse_btn)
        box.append(row)
        self._wow_status = Gtk.Label(label="")
        self._wow_status.set_xalign(0.0)
        box.append(self._wow_status)
        return box

    def _page_langs(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.append(self._title(tr("wizard.lang.title")))
        box.append(self._body(tr("wizard.lang.own")))
        self._own_lang = self._dropdown(_LANGS, self._config.own_language or "EN")
        box.append(self._own_lang)
        box.append(self._body(tr("wizard.lang.target")))
        self._target_lang = self._dropdown(_LANGS, self._config.target_language or "EN")
        box.append(self._target_lang)
        return box

    def _page_ready(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.append(self._title(tr("wizard.ready.title")))
        self._summary = self._body("")
        box.append(self._summary)
        box.append(self._body(tr("wizard.ready.closing")))
        return box

    def _entered(self, provider_id: str) -> dict[str, str]:
        return {key: entry.get_text().strip() for key, entry in self._provider_entries[provider_id].items()}

    def _refresh_summary(self) -> None:
        rows = [
            f"{GLib.markup_escape_text(spec.display_name)}: "
            f"<b>{'set' if spec.is_configured(self._entered(spec.id)) else 'not set'}</b>"
            for spec in all_providers()
        ]
        rows.append(f"WoW path: <b>{GLib.markup_escape_text(self._wow_entry.get_text().strip() or 'not set')}</b>")
        rows.append(f"Own language: <b>{self._dd_code(self._own_lang)}</b>")
        rows.append(f"Target language: <b>{self._dd_code(self._target_lang)}</b>")
        self._summary.set_markup("\n".join(rows))

    # ── API validation (off-thread) ───────────────────────────────────────
    def _has_any_key(self) -> bool:
        return any(spec.is_configured(self._entered(spec.id)) for spec in all_providers())

    def _validate_provider(self, btn: Gtk.Button, provider_id: str) -> None:
        spec = provider_get(provider_id)
        if spec is None:
            return
        values = self._entered(provider_id)
        if not spec.is_configured(values):
            self._api_status.set_markup(f'<span foreground="#cc6666">{tr("settings.api.no_key")}</span>')
            return
        self._run_validation(btn, lambda: spec.validate(values), spec.display_name)

    def _run_validation(self, btn: Gtk.Button, fn, name: str) -> None:
        btn.set_sensitive(False)
        self._api_status.set_markup(f'<span foreground="#cccc66">{tr("wizard.api.validating")}</span>')

        def worker() -> None:
            try:
                valid, msg = fn()
            except Exception as exc:  # noqa: BLE001
                valid, msg = False, str(exc)
            GLib.idle_add(done, valid, msg)

        def done(valid: bool, msg: str) -> bool:
            # Switching the interface language rebuilds every page, so the
            # button this validation started from may no longer be in the
            # window by the time the worker answers. Its replacement is
            # sensitive already; poking the orphan only earns GTK criticals.
            if btn.get_parent() is not None:
                btn.set_sensitive(True)
            if valid:
                extra = f" — {msg}" if msg and msg != "valid" else ""
                self._api_status.set_markup(
                    f'<span foreground="#66cc66">✓ {GLib.markup_escape_text(name)}: '
                    f'{tr("settings.api.valid")}{GLib.markup_escape_text(extra)}</span>'
                )
            else:
                nice = {"auth_failed": tr("settings.api.invalid"), "no_key": tr("settings.api.no_key")}.get(msg, msg)
                self._api_status.set_markup(
                    f'<span foreground="#cc6666">✗ {name}: {GLib.markup_escape_text(nice)}</span>'
                )
            return False

        threading.Thread(target=worker, daemon=True).start()

    # ── WoW path helpers ──────────────────────────────────────────────────
    def _auto_detect(self, _btn: Gtk.Button) -> None:
        path = detect_wow_path()
        if path:
            self._wow_entry.set_text(path)
            self._wow_status.set_markup(f'<span foreground="#66cc66">{tr("wizard.wow.found")}</span>')
        else:
            self._wow_status.set_markup(
                f'<span foreground="#cc6666">{tr("wizard.wow.not_found")}</span>'
            )

    def _browse(self, _btn: Gtk.Button) -> None:
        dialog = Gtk.FileDialog(title=tr("wizard.wow.browse_title"))

        def picked(dlg: Gtk.FileDialog, res) -> None:
            try:
                folder = dlg.select_folder_finish(res)
            except GLib.Error:
                return
            if folder is not None:
                self._wow_entry.set_text(folder.get_path() or "")

        dialog.select_folder(self, None, picked)

    # ── finish ────────────────────────────────────────────────────────────
    def _finish(self) -> None:
        c = self._config
        providers: dict[str, dict[str, str]] = {}
        for spec in all_providers():
            values = {key: value for key, value in self._entered(spec.id).items() if value}
            # Keyless providers are configured by existing — see the Qt copy.
            if values or spec.keyless:
                providers[spec.id] = values
        c.providers = providers
        c.translator_priority = self._dd_code(self._priority)
        c.wow_path = self._wow_entry.get_text().strip()
        c.own_language = self._dd_code(self._own_lang)
        c.target_language = self._dd_code(self._target_lang)
        c.ui_language = self._dd_code(self._ui_lang)
        c.save()
        self._result["config"] = c
        self.close()


def run_setup_wizard(config: AppConfig) -> AppConfig | None:
    """Run the wizard in its own blocking GTK loop.

    Returns the saved config, or None if the user closed without finishing.
    """
    result: dict = {"config": None}
    app = Gtk.Application(application_id="com.babelchat.SetupWizard")

    def on_activate(a: Gtk.Application) -> None:
        _WizardWindow(a, config, result).present()

    app.connect("activate", on_activate)
    app.run(None)
    return result["config"]
