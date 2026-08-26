"""GTK4 settings window for BabelChat.

A normal (non-layer-shell) window — it needs to be freely movable, closable, and
able to take keyboard input, which a regular GTK window does natively. Edits are
written to config.json on Save; an on_saved callback lets the app apply changes
to the running pipeline/overlay live (channels, languages, etc.).

Covers: channels, languages (own/target/UI), translator priority + API keys,
overlay appearance (theme presets, colors, font, corner radius), and the
skip-own-messages toggle.
"""

from __future__ import annotations

from collections.abc import Callable  # noqa: E402

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk, PangoCairo  # noqa: E402

from app.config import CHANNEL_TOGGLES, AppConfig  # noqa: E402
from app.i18n import UI_LANGUAGES, tr  # noqa: E402
from app.languages import LANGUAGES  # noqa: E402
from app.overlay_theme import (  # noqa: E402
    PRESET_LABELS,
    PRESET_ORDER,
    PRESETS,
    SLOT_LABELS,
    SLOT_ORDER,
    resolve_theme,
)
from app.translators import all_providers  # noqa: E402

# Languages messages can be translated into, named in themselves. The Qt
# dialog has always shown all of them; this list held eleven bare codes.
_LANGS = list(LANGUAGES)

# Languages the interface itself exists in. Offering more than these was a
# checkbox that silently did nothing: anything outside RU/EN/ES falls back to
# Russian in `tr`, so eight of the eleven entries here changed nothing at all.
_UI_LANGS = list(UI_LANGUAGES)

_DEFAULT_FONT = "System default"
# Curated overlay-friendly fonts; only the ones actually installed are shown.
# The generic Pango families (Sans/Serif/Monospace) always resolve.
_COMMON_FONTS = [
    "Sans",
    "Serif",
    "Monospace",
    "DejaVu Sans",
    "Noto Sans",
    "Liberation Sans",
    "Cantarell",
    "Ubuntu",
    "Inter",
    "Roboto",
    "Open Sans",
    "Fira Sans",
    "Hack",
    "Hack Nerd Font",
    "JetBrains Mono",
    "Fira Code",
]


def _installed_font_options() -> list[str]:
    """Curated fonts filtered to what's installed, generics always included."""
    try:
        families = {f.get_name().lower() for f in PangoCairo.FontMap.get_default().list_families()}
    except Exception:  # noqa: BLE001 — never break settings over font probing
        families = set()
    generics = {"sans", "serif", "monospace"}
    return [f for f in _COMMON_FONTS if f.lower() in generics or f.lower() in families]


class SettingsWindowGtk:
    """Settings editor. Construct with the live AppConfig and an on_saved cb."""

    def __init__(
        self,
        config: AppConfig,
        on_saved: Callable[[AppConfig], None] | None = None,
        app: Gtk.Application | None = None,
    ) -> None:
        self._config = config
        self._on_saved = on_saved
        self._checks: dict[str, Gtk.CheckButton] = {}

        self._win = Gtk.Window()
        if app is not None:
            self._win.set_application(app)
        self._win.set_title(tr("settings.title"))
        self._win.set_default_size(460, 640)
        self._build()

    def present(self) -> None:
        self._win.present()

    # ── UI ────────────────────────────────────────────────────────────────
    def _build(self) -> None:
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.set_margin_top(16)
        root.set_margin_bottom(16)
        root.set_margin_start(16)
        root.set_margin_end(16)

        # Channels
        root.append(self._section(tr("settings.channels_group")))
        grid = Gtk.Grid()
        grid.set_row_spacing(4)
        grid.set_column_spacing(16)
        for i, toggle in enumerate(CHANNEL_TOGGLES):
            cb = Gtk.CheckButton(label=tr(toggle.label))
            cb.set_active(bool(getattr(self._config, toggle.field)))
            self._checks[toggle.field] = cb
            grid.attach(cb, i % 2, i // 2, 1, 1)
        root.append(grid)

        # Languages
        root.append(self._section(tr("settings.lang_group")))
        self._own = self._combo_row(root, tr("settings.lang.own"), self._config.own_language)
        self._target = self._combo_row(root, tr("settings.lang.target"), self._config.target_language)
        self._ui = self._combo_row(root, tr("settings.lang.ui"), self._config.ui_language, options=_UI_LANGS)

        # Translation API
        root.append(self._section(tr("settings.api_group")))
        self._priority = self._combo_row(
            root,
            tr("settings.api.preferred"),
            self._config.translator_priority,
            options=[spec.id for spec in all_providers()],
        )
        # One row per credential the provider declares — nothing here names a
        # provider, so a new one appears in these settings on its own.
        saved = self._config.providers or {}
        self._provider_entries: dict[str, dict[str, object]] = {}
        for spec in all_providers():
            values = saved.get(spec.id, {})
            if spec.guide:
                guide = Gtk.LinkButton(uri=spec.guide, label=f"{spec.display_name}: {tr('provider.guide')}")
                guide.set_halign(Gtk.Align.START)
                root.append(guide)
            self._provider_entries[spec.id] = {
                pfield.key: self._entry_row(
                    root,
                    f"{spec.display_name} — {pfield.label_text()}",
                    values.get(pfield.key, ""),
                    secret=pfield.secret,
                )
                for pfield in spec.fields
            }

        # Appearance
        root.append(self._section(tr("settings.appearance_group")))
        self._opacity = self._scale_row(root, tr("settings.overlay.opacity"), self._config.overlay_opacity, 40, 255)
        self._font = self._scale_row(root, tr("settings.overlay.font_size"), self._config.overlay_font_size, 8, 28)
        self._build_appearance(root)

        # Behavior
        root.append(self._section(tr("settings.behavior_group")))
        self._skip_own = Gtk.CheckButton(label=tr("settings.overlay.skip_own_messages"))
        self._skip_own.set_active(bool(self._config.skip_own_messages))
        root.append(self._skip_own)

        # Actions
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        save = Gtk.Button(label=tr("settings.save"))
        save.connect("clicked", self._on_save)
        close = Gtk.Button(label=tr("settings.close"))
        close.connect("clicked", lambda _b: self._win.close())
        self._status = Gtk.Label(label="")
        self._status.set_hexpand(True)
        self._status.set_xalign(0.0)
        actions.append(save)
        actions.append(close)
        actions.append(self._status)
        root.append(actions)

        scroller.set_child(root)
        self._win.set_child(scroller)

    # ── appearance (theme) UI ─────────────────────────────────────────────
    def _build_appearance(self, root: Gtk.Box) -> None:
        cfg = self._config
        theme = resolve_theme(cfg)
        self._suppress_custom = True  # don't flip to Custom while populating

        # Preset dropdown
        labels = [PRESET_LABELS[p] for p in PRESET_ORDER]
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=tr("settings.theme_preset"))
        lbl.set_xalign(0.0)
        lbl.set_size_request(140, -1)
        self._preset = Gtk.DropDown.new_from_strings(labels)
        cur = cfg.overlay_theme if cfg.overlay_theme in PRESET_ORDER else "custom"
        self._preset.set_selected(PRESET_ORDER.index(cur))
        self._preset.connect("notify::selected", self._on_preset_changed)
        row.append(lbl)
        row.append(self._preset)
        root.append(row)

        # Base colors
        self._col_bg = self._color_row(root, tr("settings.color.background"), theme.bg_color)
        self._col_ts = self._color_row(root, tr("settings.color.timestamp"), theme.timestamp_color)
        self._col_orig = self._color_row(root, tr("settings.color.original"), theme.original_color)
        self._col_tl = self._color_row(root, tr("settings.color.translated"), theme.translation_color)

        # Corner radius
        self._radius = self._scale_row(root, tr("settings.overlay.corner_radius"), theme.corner_radius, 0, 24)
        self._radius.connect("value-changed", lambda _s: self._mark_custom())

        # Font family: dropdown of common installed fonts, still free-typable
        frow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        flbl = Gtk.Label(label=tr("settings.overlay.font"))
        flbl.set_xalign(0.0)
        flbl.set_size_request(140, -1)
        self._font_family = Gtk.ComboBoxText.new_with_entry()
        self._font_family.set_hexpand(True)
        options = [_DEFAULT_FONT, *_installed_font_options()]
        for opt in options:
            self._font_family.append_text(opt)
        current = cfg.overlay_font_family or ""
        if not current:
            self._font_family.set_active(0)
        elif current in options:
            self._font_family.set_active(options.index(current))
        else:
            self._font_family.get_child().set_text(current)
        frow.append(flbl)
        frow.append(self._font_family)
        root.append(frow)

        # Title bar button colors
        bexp = Gtk.Expander(label=tr("settings.titlebar_colors"))
        bgrid = Gtk.Grid()
        bgrid.set_row_spacing(4)
        bgrid.set_column_spacing(8)
        bgrid.set_margin_top(6)
        self._bar_buttons: dict[str, Gtk.ColorButton] = {}
        for i, (key, label, color) in enumerate((
            ("tl_on", "TR: ON toggle", theme.tl_on_color),
            ("tl_off", "TR: OFF toggle", theme.tl_off_color),
            ("close", "Close button", theme.close_color),
            ("tool", "Other buttons", theme.tool_color),
        )):
            blbl = Gtk.Label(label=label)
            blbl.set_xalign(0.0)
            btn = self._color_button(color)
            self._bar_buttons[key] = btn
            bgrid.attach(blbl, 0, i, 1, 1)
            bgrid.attach(btn, 1, i, 1, 1)
        bexp.set_child(bgrid)
        root.append(bexp)

        # Per-channel colors
        exp = Gtk.Expander(label=tr("settings.channel_colors"))
        grid = Gtk.Grid()
        grid.set_row_spacing(4)
        grid.set_column_spacing(8)
        grid.set_margin_top(6)
        self._slot_buttons: dict[str, Gtk.ColorButton] = {}
        for i, slot in enumerate(SLOT_ORDER):
            slbl = Gtk.Label(label=SLOT_LABELS[slot])
            slbl.set_xalign(0.0)
            btn = self._color_button(theme.channel_colors.get(slot, "#FFFFFF"))
            self._slot_buttons[slot] = btn
            grid.attach(slbl, 0, i, 1, 1)
            grid.attach(btn, 1, i, 1, 1)
        exp.set_child(grid)
        root.append(exp)

        self._suppress_custom = False

    def _color_button(self, hex_color: str) -> Gtk.ColorButton:
        rgba = Gdk.RGBA()
        rgba.parse(hex_color)
        btn = Gtk.ColorButton()
        btn.set_rgba(rgba)
        btn.connect("color-set", lambda _b: self._mark_custom())
        return btn

    def _color_row(self, parent: Gtk.Box, label: str, hex_color: str) -> Gtk.ColorButton:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=label)
        lbl.set_xalign(0.0)
        lbl.set_size_request(140, -1)
        btn = self._color_button(hex_color)
        row.append(lbl)
        row.append(btn)
        parent.append(row)
        return btn

    @staticmethod
    def _rgba_hex(btn: Gtk.ColorButton) -> str:
        c = btn.get_rgba()
        return f"#{round(c.red * 255):02X}{round(c.green * 255):02X}{round(c.blue * 255):02X}"

    def _mark_custom(self) -> None:
        """Any manual color/radius edit switches the preset to Custom."""
        if getattr(self, "_suppress_custom", True):
            return
        self._preset.set_selected(PRESET_ORDER.index("custom"))

    def _on_preset_changed(self, dd: Gtk.DropDown, _p: object) -> None:
        if getattr(self, "_suppress_custom", True):
            return
        name = PRESET_ORDER[dd.get_selected()]
        if name == "custom" or name not in PRESETS:
            return
        theme = PRESETS[name]
        self._suppress_custom = True
        rgba = Gdk.RGBA()
        for btn, color in (
            (self._col_bg, theme.bg_color),
            (self._col_ts, theme.timestamp_color),
            (self._col_orig, theme.original_color),
            (self._col_tl, theme.translation_color),
        ):
            rgba.parse(color)
            btn.set_rgba(rgba)
        for slot, btn in self._slot_buttons.items():
            rgba.parse(theme.channel_colors.get(slot, "#FFFFFF"))
            btn.set_rgba(rgba)
        for key, btn in self._bar_buttons.items():
            rgba.parse(getattr(theme, f"{key}_color"))
            btn.set_rgba(rgba)
        self._radius.set_value(theme.corner_radius)
        self._suppress_custom = False

    def _section(self, text: str) -> Gtk.Label:
        lbl = Gtk.Label()
        lbl.set_markup(f"<b>{text}</b>")
        lbl.set_xalign(0.0)
        lbl.set_margin_top(6)
        return lbl

    def _entry_row(self, parent: Gtk.Box, label: str, value: str, secret: bool = False) -> Gtk.Entry:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=label)
        lbl.set_width_chars(18)
        lbl.set_xalign(0.0)
        entry = Gtk.Entry()
        entry.set_text(value or "")
        entry.set_hexpand(True)
        if secret:
            entry.set_visibility(False)
        row.append(lbl)
        row.append(entry)
        parent.append(row)
        return entry

    def _combo_row(self, parent: Gtk.Box, label: str, value: str, options: list[str] | None = None) -> Gtk.DropDown:
        opts = options or _LANGS
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=label)
        lbl.set_width_chars(18)
        lbl.set_xalign(0.0)
        model = Gtk.StringList()
        for o in opts:
            model.append(o)
        dd = Gtk.DropDown(model=model)
        try:
            dd.set_selected(opts.index(value))
        except ValueError:
            dd.set_selected(0)
        dd._opts = opts  # stash for read-back
        row.append(lbl)
        row.append(dd)
        parent.append(row)
        return dd

    def _scale_row(self, parent: Gtk.Box, label: str, value: int, lo: int, hi: int) -> Gtk.Scale:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=label)
        lbl.set_width_chars(18)
        lbl.set_xalign(0.0)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lo, hi, 1)
        scale.set_value(value)
        scale.set_hexpand(True)
        scale.set_draw_value(True)
        row.append(lbl)
        row.append(scale)
        parent.append(row)
        return scale

    # ── save ──────────────────────────────────────────────────────────────
    def _dd_value(self, dd: Gtk.DropDown) -> str:
        opts = getattr(dd, "_opts", _LANGS)
        idx = dd.get_selected()
        return opts[idx] if 0 <= idx < len(opts) else opts[0]

    def _on_save(self, _btn: Gtk.Button) -> None:
        c = self._config
        for attr, cb in self._checks.items():
            setattr(c, attr, cb.get_active())
        c.own_language = self._dd_value(self._own)
        c.target_language = self._dd_value(self._target)
        language_changed = self._dd_value(self._ui) != tr.get_language()
        c.ui_language = self._dd_value(self._ui)
        # Applied immediately, the way the Qt dialog does it: a language you
        # picked and saved that does not take hold reads as the setting being
        # broken.
        tr.set_language(c.ui_language)
        c.translator_priority = self._dd_value(self._priority)
        providers: dict[str, dict[str, str]] = {}
        for spec in all_providers():
            entries = self._provider_entries.get(spec.id, {})
            values = {key: entry.get_text().strip() for key, entry in entries.items()}
            values = {key: value for key, value in values.items() if value}
            # Keyless providers are configured by existing — see the Qt copy.
            if values or spec.keyless:
                providers[spec.id] = values
        c.providers = providers
        c.overlay_opacity = int(self._opacity.get_value())
        c.overlay_font_size = int(self._font.get_value())
        c.overlay_theme = PRESET_ORDER[self._preset.get_selected()]
        c.overlay_bg_color = self._rgba_hex(self._col_bg)
        c.overlay_timestamp_color = self._rgba_hex(self._col_ts)
        c.overlay_original_color = self._rgba_hex(self._col_orig)
        c.overlay_translation_color = self._rgba_hex(self._col_tl)
        c.overlay_corner_radius = int(self._radius.get_value())
        family = self._font_family.get_child().get_text().strip()
        c.overlay_font_family = "" if family == _DEFAULT_FONT else family
        c.overlay_channel_colors = {slot: self._rgba_hex(btn) for slot, btn in self._slot_buttons.items()}
        c.overlay_tl_on_color = self._rgba_hex(self._bar_buttons["tl_on"])
        c.overlay_tl_off_color = self._rgba_hex(self._bar_buttons["tl_off"])
        c.overlay_close_color = self._rgba_hex(self._bar_buttons["close"])
        c.overlay_tool_color = self._rgba_hex(self._bar_buttons["tool"])
        c.skip_own_messages = self._skip_own.get_active()

        try:
            c.save()
            self._status.set_markup(f'<span foreground="#33aa33">{tr("settings.saved")}</span>')
        except Exception as exc:  # noqa: BLE001
            message = GLib.markup_escape_text(tr("settings.save_failed", detail=exc))
            self._status.set_markup(f'<span foreground="#cc3333">{message}</span>')
            return

        if self._on_saved is not None:
            self._on_saved(c)

        # Every label in here was built in the old language and a GTK widget
        # keeps the string it was built with, so a language change has to close
        # the window: the next opening is the rebuild. Any other save leaves it
        # open — closing on all of them would mean the "Saved" just written two
        # lines up is never on screen long enough to read.
        if language_changed:
            self._win.close()
