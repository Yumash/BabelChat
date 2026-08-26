"""GTK4 + gtk4-layer-shell overlay frontend for BabelChat.

This replaces the PyQt6 overlay on Linux/Wayland. A layer-shell surface on the
OVERLAY layer sits above true-fullscreen games (which a normal always-on-top
window cannot do on Wayland). Keyboard mode ON_DEMAND lets the reply box take
focus on click without stealing keystrokes during gameplay.

The engine/pipeline (app.pipeline / app.translator) are framework-agnostic and
reused unchanged. The pipeline runs in a background thread and delivers
TranslatedMessage objects via a callback; we marshal those onto the GTK main
loop with GLib.idle_add.

Stage 1 scope: streaming chat display + always-present reply box.
Settings and tray are handled elsewhere / later.
"""

from __future__ import annotations

# gtk4-layer-shell MUST be loaded before libwayland-client (i.e. before gi pulls
# in GTK). Loading the shared object explicitly guarantees link order.
import logging as _logging
import os as _os
import sys as _sys
from ctypes import CDLL


def _load_layer_shell() -> bool:
    """Preload libgtk4-layer-shell before gi imports GTK, if it is available.

    Must happen before `gi` pulls in libwayland-client. In a PyInstaller
    bundle the .so is placed under sys._MEIPASS (not on the system loader
    path), so try the bundled copy first, then fall back to the system name.

    Returns True if the library was loaded. A missing library is NOT fatal:
    layer-shell is only needed for the Wayland layer mode, and X11-only
    distros often don't package it. Callers below fall back to X11/plain when
    the Gtk4LayerShell typelib can't be imported, so here we only warn and let
    that path take over — raising would crash the app before the fallback the
    surrounding code already provides could ever run.
    """
    candidates = []
    meipass = getattr(_sys, "_MEIPASS", None)
    if meipass:
        # Bundled next to the executable contents.
        for name in ("libgtk4-layer-shell.so", "libgtk4-layer-shell.so.0"):
            candidates.append(_os.path.join(meipass, name))
    # System-installed fallback (normal `python -m app.main_gtk` run).
    candidates += ["libgtk4-layer-shell.so", "libgtk4-layer-shell.so.0"]

    last_err = None
    for cand in candidates:
        try:
            CDLL(cand)
            return True
        except OSError as exc:  # not found at this path; try next
            last_err = exc
    _logging.getLogger(__name__).warning(
        "gtk4-layer-shell not loadable (%s); the Wayland overlay layer is "
        "unavailable, falling back to X11/plain. Install gtk4-layer-shell for "
        "the layer-shell overlay (e.g. `sudo pacman -S gtk4-layer-shell`).",
        last_err,
    )
    return False


_layer_shell_loaded = _load_layer_shell()

import contextlib
import logging
import threading  # noqa: E402
from collections.abc import Callable  # noqa: E402

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk, Pango  # noqa: E402

# gtk4-layer-shell is only needed for the Wayland layer mode; X11-only
# distros often don't package it, and the x11/plain fallbacks must still run.
try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402
except (ValueError, ImportError):  # typelib not installed
    LayerShell = None

from app.config import FILTER_TABS, AppConfig
from app.i18n import tr
from app.overlay_theme import OverlayTheme, dim, hex_to_rgb, resolve_theme  # noqa: E402
from app.parser import Channel  # noqa: E402
from app.pipeline import TranslatedMessage  # noqa: E402
from app.translator import TranslatorService  # noqa: E402
from app.x11_window import apply_overlay_hints, get_xid, move_window  # noqa: E402

logger = logging.getLogger(__name__)

# Channel → theme color slot (see app/overlay_theme.py). Related channels share
# a slot the same way WoW colors them; the active theme supplies the colors.
_CHANNEL_SLOT: dict[Channel, str] = {
    Channel.SAY: "say",
    Channel.YELL: "yell",
    Channel.PARTY: "party",
    Channel.PARTY_LEADER: "party",
    Channel.RAID: "raid",
    Channel.RAID_LEADER: "raid",
    Channel.RAID_WARNING: "raid_warning",
    Channel.GUILD: "guild",
    Channel.OFFICER: "officer",
    Channel.WHISPER_FROM: "whisper",
    Channel.WHISPER_TO: "whisper",
    Channel.INSTANCE: "instance",
    Channel.INSTANCE_LEADER: "instance",
    Channel.TRADE: "public",
    Channel.GENERAL: "public",
    Channel.SERVICES: "public",
    Channel.LOOKING_FOR_GROUP: "public",
}

_CHANNEL_BADGE: dict[Channel, str] = {
    Channel.SAY: "[Say]",
    Channel.YELL: "[Yell]",
    Channel.PARTY: "[P]",
    Channel.PARTY_LEADER: "[PL]",
    Channel.RAID: "[R]",
    Channel.RAID_LEADER: "[RL]",
    Channel.RAID_WARNING: "[RW]",
    Channel.GUILD: "[G]",
    Channel.OFFICER: "[O]",
    Channel.WHISPER_FROM: "[W From]",
    Channel.WHISPER_TO: "[W To]",
    Channel.INSTANCE: "[I]",
    Channel.INSTANCE_LEADER: "[IL]",
    Channel.TRADE: "[Trade]",
    Channel.GENERAL: "[Gen]",
    Channel.SERVICES: "[Svc]",
    Channel.LOOKING_FOR_GROUP: "[LFG]",
}

_MAX_ROWS = 200
_APP_ID = "com.babelchat.Overlay"
_WOW_STATUS_INTERVAL = 2  # seconds between WoW connection status polls
_MIN_W = 240
_MIN_H = 140
# Languages offered in the reply target-language selector (ISO codes).
_REPLY_LANGS = ["EN", "RU", "ES", "DE", "FR", "PT", "IT", "PL", "ZH", "KO", "JA"]

# Filter-tab name → the channels it shows. "All" shows everything.
_FILTER_CHANNELS: dict[str, set[Channel]] = {
    "All": set(Channel),
    "Say": {Channel.SAY, Channel.YELL},
    "Party": {Channel.PARTY, Channel.PARTY_LEADER},
    "Raid": {Channel.RAID, Channel.RAID_LEADER, Channel.RAID_WARNING},
    "Guild": {Channel.GUILD, Channel.OFFICER},
    "Whisper": {Channel.WHISPER_FROM, Channel.WHISPER_TO},
    "Instance": {Channel.INSTANCE, Channel.INSTANCE_LEADER},
    "Trade": {Channel.TRADE},
    "General": {Channel.GENERAL},
    "Services": {Channel.SERVICES},
    "LFG": {Channel.LOOKING_FOR_GROUP},
}
# Order of the filter tabs in the bar, from the shared declaration. The list
# that used to live here was written in English and shown as written, whatever
# language the rest of the interface was in — and it said "LFG" where the
# channel is called LookingForGroup, so that tab matched nothing.
_FILTER_ORDER = [name for name, _key in FILTER_TABS]
_FILTER_LABELS = dict(FILTER_TABS)


class _MessageRow(Gtk.Box):
    """One chat line: '[badge] Author: original → translation'.

    Supports in-place update of the translation when a streaming update with the
    same msg_id arrives (original shown first, translation filled in later).
    """

    def __init__(self, msg: TranslatedMessage, font_px: int, theme: OverlayTheme) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._font_px = font_px
        self._theme = theme
        self._msg = msg
        self.channel = msg.original.channel  # used by the filter bar
        self._label = Gtk.Label()
        self._label.set_xalign(0.0)
        self._label.set_wrap(True)
        self._label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._label.set_selectable(False)
        self.append(self._label)
        self.update_content(msg)

    def update_content(self, msg: TranslatedMessage) -> None:
        self._msg = msg
        cm = msg.original
        theme = self._theme
        slot = _CHANNEL_SLOT.get(cm.channel, "say")
        color = theme.channel_colors.get(slot, theme.text_color)
        badge = _CHANNEL_BADGE.get(cm.channel, "")
        esc = GLib.markup_escape_text
        author = esc(cm.author or "")
        original = esc(cm.text or "")

        # Dim "21:30 " prefix, matching the Windows overlay.
        ts = cm.timestamp or ""
        time_part = ts.split(" ", 1)[-1] if " " in ts else ts
        short_time = ":".join(time_part.split(":")[:2])
        stamp = (
            f'<span foreground="{theme.timestamp_color}">{esc(short_time)} </span>'
            if short_time
            else ""
        )

        head = (
            f'{stamp}<span foreground="{color}">'
            f"{esc(badge)} <b>{author}</b>:</span>"
        )
        if msg.translation and msg.translation.success and msg.translation.translated:
            translated = esc(msg.translation.translated)
            body = (
                f'<span foreground="{theme.original_color}"> {original}</span>'
                f'<span foreground="{theme.translation_color}"> → {translated}</span>'
            )
        else:
            # No translation (yet) — channel color, like the Windows overlay.
            body = f'<span foreground="{color}"> {original}</span>'

        self._label.set_markup(f'<span size="{self._font_px * 1000}">{head}{body}</span>')

    def restyle(self, font_px: int, theme: OverlayTheme) -> None:
        """Re-render with a new theme/font (live settings apply)."""
        self._font_px = font_px
        self._theme = theme
        self.update_content(self._msg)


class ChatOverlayGtk:
    """The GTK4 layer-shell overlay application wrapper."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._theme: OverlayTheme = resolve_theme(config)
        # "layer" (Wayland + layer-shell), "x11" (EWMH always-on-top), or
        # "plain" (no overlay mechanism, e.g. GNOME Wayland).
        self._mode: str = "layer"
        self._translator: TranslatorService | None = None
        self._reply_lang = "EN"
        self._rows: dict[int, _MessageRow] = {}  # msg_id → row (streaming updates)
        self._row_order: list[int] = []          # insertion order for trimming
        self._margin_top: int = 0
        self._margin_left: int = 0
        self._drag_start: tuple[int, int] = (0, 0)
        self._active_filter: str = "All"
        self._pending: list[TranslatedMessage] = []  # queued before window build
        self._cur_w: int = 0
        self._cur_h: int = 0

        self._app = Gtk.Application(application_id=_APP_ID)
        self._app.connect("activate", self._on_activate)

        # Built in _on_activate:
        self._win: Gtk.ApplicationWindow | None = None
        self._list: Gtk.Box | None = None
        self._scroller: Gtk.ScrolledWindow | None = None
        self._reply_entry: Gtk.Entry | None = None
        self._grip: Gtk.DrawingArea | None = None
        self._reply_status: Gtk.Label | None = None

        # Callbacks wired by main (so this module stays UI-only).
        self.on_quit: Callable[[], None] | None = None
        self.on_visibility_changed: Callable[[bool], None] | None = None
        self.on_settings: Callable[[], None] | None = None
        self.on_reply_send: Callable[[str], None] | None = None
        self.on_toggle_translation: Callable[[bool], None] | None = None

    # ── lifecycle ─────────────────────────────────────────────────────────
    def run(self) -> int:
        return self._app.run(None)

    def set_translator(self, translator: TranslatorService, reply_lang: str) -> None:
        self._translator = translator
        self._reply_lang = reply_lang
        # Keep the reply-language dropdown in sync if it exists.
        dd = getattr(self, "_reply_lang_dd", None)
        if dd is not None:
            with contextlib.suppress(ValueError):
                dd.set_selected(_REPLY_LANGS.index(reply_lang))

    # ── message delivery (thread-safe entry point) ───────────────────────
    def deliver_message(self, msg: TranslatedMessage) -> None:
        """Called from the pipeline thread; marshal onto the GTK main loop."""
        GLib.idle_add(self._add_or_update_row, msg)

    def _add_or_update_row(self, msg: TranslatedMessage) -> bool:
        if self._list is None:
            # Window not built yet (history load / early pipeline messages):
            # queue and flush when the UI is ready instead of dropping.
            self._pending.append(msg)
            return False

        font_px = max(8, int(self._config.overlay_font_size or 12))
        # Capture BEFORE mutating the list: only auto-scroll if the user is
        # already at (or near) the bottom, so reading history isn't yanked away.
        was_at_bottom = self._is_at_bottom()

        if msg.is_update and msg.msg_id in self._rows:
            self._rows[msg.msg_id].update_content(msg)
            if was_at_bottom:
                self._scroll_to_bottom()
            return False  # one-shot idle

        row = _MessageRow(msg, font_px, self._theme)
        self._rows[msg.msg_id] = row
        self._row_order.append(msg.msg_id)
        self._list.append(row)
        # Respect the active filter for newly-arrived messages.
        if self._active_filter != "All":
            allowed = _FILTER_CHANNELS.get(self._active_filter, set(Channel))
            row.set_visible(row.channel in allowed)

        # Trim oldest rows beyond the cap.
        while len(self._row_order) > _MAX_ROWS:
            old_id = self._row_order.pop(0)
            old_row = self._rows.pop(old_id, None)
            if old_row is not None:
                self._list.remove(old_row)

        if was_at_bottom:
            self._scroll_to_bottom()
        return False  # remove this idle source after running once

    def _is_at_bottom(self) -> bool:
        if self._scroller is None:
            return True
        adj = self._scroller.get_vadjustment()
        # 40px tolerance so tiny sub-row offsets still count as "at bottom".
        return adj.get_value() >= adj.get_upper() - adj.get_page_size() - 40

    def _scroll_to_bottom(self) -> None:
        if self._scroller is None:
            return

        def _do() -> bool:
            adj = self._scroller.get_vadjustment()
            adj.set_value(adj.get_upper() - adj.get_page_size())
            return False

        # Defer one tick so the new row is laid out before we scroll.
        GLib.idle_add(_do)

    # ── UI construction ───────────────────────────────────────────────────
    def _show_plain_mode_notice(self, win: Gtk.Window) -> None:
        """One-time heads-up when no overlay mechanism exists (GNOME Wayland)."""
        if getattr(self._config, "fallback_notice_shown", False):
            return
        self._config.fallback_notice_shown = True
        with contextlib.suppress(Exception):
            self._config.save()
        msg = (
            "This compositor doesn't support overlay windows (no layer-shell "
            "protocol — this is the case on GNOME Wayland), so BabelChat is "
            "running as a regular window.\n\n"
            "Tip: right-click the title bar and enable \u201cAlways on "
            "Top\u201d, and run the game in borderless windowed mode."
        )
        try:
            dlg = Gtk.AlertDialog()
            dlg.set_message("Overlay not available on this desktop")
            dlg.set_detail(msg)
            dlg.show(win)
        except Exception:  # noqa: BLE001 — a missing dialog must not break startup
            logger.info("plain mode notice: %s", msg)

    def _detect_mode(self) -> str:
        """Pick the overlay mechanism for the current session.

        Wayland + a compositor that advertises layer-shell → "layer".
        X11 (or XWayland) → "x11": EWMH _NET_WM_STATE_ABOVE fallback.
        Anything else (notably GNOME Wayland, where Mutter refuses the
        layer-shell protocol) → "plain" regular window.
        """
        display = Gdk.Display.get_default()
        backend = type(display).__name__ if display is not None else ""
        if "Wayland" in backend:
            try:
                if LayerShell is not None and LayerShell.is_supported():
                    return "layer"
            except Exception:  # noqa: BLE001 — old bindings without is_supported
                logger.debug("layer-shell support probe failed", exc_info=True)
            return "plain"
        if "X11" in backend:
            return "x11"
        return "plain"

    def _sync_cur_size(self) -> None:
        """Refresh tracked size from the real window (WMs may constrain it)."""
        if self._win is not None:
            w, h = self._win.get_width(), self._win.get_height()
            if w > 0 and h > 0:
                self._cur_w, self._cur_h = w, h

    def _position_ghost(self, ghost: Gtk.Window, top: int, left: int) -> None:
        if self._mode == "layer":
            LayerShell.set_margin(ghost, LayerShell.Edge.TOP, top)
            LayerShell.set_margin(ghost, LayerShell.Edge.LEFT, left)
        elif self._mode == "x11":
            xid = get_xid(ghost)
            if xid:
                move_window(xid, left, top)

    def _make_ghost(self, width: int, height: int, top: int, left: int) -> Gtk.Window:
        """Create a transparent layer-shell outline window for drag feedback."""
        ghost = Gtk.Window()
        ghost.set_default_size(width, height)
        # Request the MIN floor (not the starting size) so the ghost can be
        # freely resized smaller during the preview — set_size_request is a
        # minimum, and pinning it to the start size would block inward preview.
        ghost.set_size_request(_MIN_W, _MIN_H)
        if self._mode == "layer":
            LayerShell.init_for_window(ghost)
            LayerShell.set_layer(ghost, LayerShell.Layer.OVERLAY)
            LayerShell.set_anchor(ghost, LayerShell.Edge.TOP, True)
            LayerShell.set_anchor(ghost, LayerShell.Edge.LEFT, True)
            LayerShell.set_margin(ghost, LayerShell.Edge.TOP, top)
            LayerShell.set_margin(ghost, LayerShell.Edge.LEFT, left)
        elif self._mode == "x11":
            ghost.set_decorated(False)

            def _ghost_mapped(g: Gtk.Window) -> None:
                xid = get_xid(g)
                if xid:
                    apply_overlay_hints(xid)
                    move_window(xid, left, top)

            ghost.connect("map", _ghost_mapped)
        # Ghost must never take input — it's purely visual feedback.
        if self._mode == "layer":
            LayerShell.set_keyboard_mode(ghost, LayerShell.KeyboardMode.NONE)
        else:
            ghost.set_can_focus(False)

        # Bright outline + faint fill so it's visible over busy game scenes.
        frame = Gtk.Box()
        frame.add_css_class("bc-ghost")
        ghost.set_child(frame)

        css = Gtk.CssProvider()
        css.load_from_data(
            b".bc-ghost { background-color: rgba(153,204,255,0.18);"
            b" border: 2px solid #99ccff; border-radius: 6px; }"
        )
        Gtk.StyleContext.add_provider_for_display(
            ghost.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        ghost.present()
        return ghost

    def _initial_margins(self, win: Gtk.Window, width: int, height: int) -> tuple[int, int]:
        """Pick initial top/left margins: stored coords if on-screen, else center.

        On multi-monitor + fractional-scaling setups the old absolute coords can
        be off-screen, so we validate against the monitor under the pointer and
        fall back to centering.
        """
        stored_top = int(self._config.overlay_y or 0)
        stored_left = int(self._config.overlay_x or 0)

        try:
            display = win.get_display()
            monitors = display.get_monitors()
            monitor = monitors.get_item(0) if monitors.get_n_items() > 0 else None
            if monitor is not None:
                geo = monitor.get_geometry()
                mon_w, mon_h = geo.width, geo.height
                # If stored position keeps the window fully on this monitor, use
                # it; otherwise center.
                if (0 <= stored_left <= max(0, mon_w - width)
                        and 0 <= stored_top <= max(0, mon_h - height)
                        and (stored_top or stored_left)):
                    return stored_top, stored_left
                center_left = max(0, (mon_w - width) // 2)
                center_top = max(0, (mon_h - height) // 2)
                return center_top, center_left
        except Exception:  # noqa: BLE001
            pass

        # Fallback if monitor geometry is unavailable.
        return 100, 100

    def _on_activate(self, app: Gtk.Application) -> None:
        # Gtk.Application is single-instance per app id: launching the binary/
        # AppImage again (e.g. from a pinned taskbar launcher) forwards a
        # second "activate" here instead of starting a new process. Treat that
        # as a show/hide toggle so the pinned icon acts like a taskbar button.
        if self._win is not None:
            self.toggle_visible()
            return
        width = max(_MIN_W, int(self._config.overlay_width or 480))
        height = max(_MIN_H, int(self._config.overlay_height or 320))
        self._cur_w = width
        self._cur_h = height
        opacity = max(0.1, min(1.0, (self._config.overlay_opacity or 200) / 255.0))

        win = Gtk.ApplicationWindow(application=app)
        win.set_default_size(width, height)
        # size_request must stay at the absolute MIN floor (not the startup
        # size) so the window can be resized smaller later. default_size above
        # gives it the actual starting size; the small request just prevents it
        # collapsing to ~0px while still allowing shrink down to the floor.
        win.set_size_request(_MIN_W, _MIN_H)

        # Layer-shell: OVERLAY layer (above fullscreen), ON_DEMAND keyboard so
        # the reply box can take focus on click without stealing gameplay input.
        # Layer-shell positioning: anchor to top-left and use margins so the
        # window can be dragged (margins are the reference frame the drag
        # adjusts). We compute initial margins that center it on the output the
        # first time, then drag/persist from there.
        self._mode = self._detect_mode()
        logger.info("overlay mode: %s", self._mode)
        if self._mode == "layer":
            LayerShell.init_for_window(win)
            LayerShell.set_layer(win, LayerShell.Layer.OVERLAY)
            LayerShell.set_anchor(win, LayerShell.Edge.TOP, True)
            LayerShell.set_anchor(win, LayerShell.Edge.LEFT, True)
            LayerShell.set_keyboard_mode(win, LayerShell.KeyboardMode.ON_DEMAND)
        elif self._mode == "x11":
            # EWMH fallback: undecorated, always-on-top, sticky, off the
            # taskbar — the same overlay behavior the PyQt frontend gets on
            # Windows/X11. Hints must be (re)sent once the window is mapped.
            win.set_decorated(False)

            def _win_mapped(w: Gtk.Window) -> None:
                xid = get_xid(w)
                if xid:
                    apply_overlay_hints(xid)
                    move_window(xid, self._margin_left, self._margin_top)

            win.connect("map", _win_mapped)
        else:
            self._show_plain_mode_notice(win)

        # Initial margins: use stored values if they look on-screen, else center
        # on the primary monitor. Stored absolute coords from the old Qt build
        # can be off-screen on multi-monitor/fractional setups, so we sanity-
        # check against the monitor geometry.
        margin_top, margin_left = self._initial_margins(win, width, height)
        self._margin_top = margin_top
        self._margin_left = margin_left
        if self._mode == "layer":
            LayerShell.set_margin(win, LayerShell.Edge.TOP, margin_top)
            LayerShell.set_margin(win, LayerShell.Edge.LEFT, margin_left)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        root.add_css_class("bc-root")

        # Top bar: title + settings/quit buttons.
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bar.add_css_class("bc-bar")
        bar.set_cursor_from_name("grab")
        title = Gtk.Label(label="BabelChat")
        title.set_xalign(0.0)
        title.set_hexpand(True)
        # WoW connection status ("WoW: ✔ / … / ✖"), polled via the checker
        # wired by main — same behavior as the PyQt overlay.
        self._wow_status = Gtk.Label(label="WoW: ?")
        self._wow_status.add_css_class("bc-wow")
        # Quick translation on/off toggle. Reflects/controls pipeline state via
        # the on_toggle_translation callback wired by main.
        active = bool(self._config.translation_enabled_default)
        self._translate_toggle = Gtk.ToggleButton(label=tr("overlay.badge.on") if active else tr("overlay.badge.off"))
        self._translate_toggle.set_active(active)
        self._translate_toggle.set_tooltip_text(tr("overlay.translate_toggle"))
        self._translate_toggle.add_css_class("bc-tl")
        self._translate_toggle.set_cursor_from_name("pointer")
        self._translate_toggle.connect("toggled", self._on_translate_toggled)
        settings_btn = Gtk.Button(label="⚙")
        settings_btn.add_css_class("bc-tool")
        settings_btn.set_cursor_from_name("pointer")
        settings_btn.connect("clicked", lambda _b: self.on_settings and self.on_settings())
        quit_btn = Gtk.Button(label="✕")
        quit_btn.add_css_class("bc-close")
        quit_btn.set_cursor_from_name("pointer")
        quit_btn.connect("clicked", lambda _b: self.on_quit and self.on_quit())
        bar.append(title)
        bar.append(self._wow_status)
        bar.append(self._translate_toggle)
        bar.append(settings_btn)
        bar.append(quit_btn)

        # Drag-to-move with a Win9x-style "ghost" outline. The real overlay
        # can't reposition smoothly (layer-surface reconfigure jitter), so during
        # the drag we show a separate lightweight layer-shell window — a bright
        # outline with a faint fill — that follows the cursor. On release the
        # ghost is destroyed and the real overlay snaps to the final spot in a
        # single set_margin (no jitter).
        drag = Gtk.GestureDrag.new()
        self._drag_start = (0, 0)
        self._ghost: Gtk.Window | None = None

        def _drag_begin(_g: Gtk.GestureDrag, _sx: float, _sy: float) -> None:
            # Only record the starting margins here. Do NOT create the ghost yet
            # — a press without movement (e.g. clicking a titlebar button) fires
            # drag-begin too, and we don't want the ghost to flash on a click.
            self._drag_start = (self._margin_top, self._margin_left)
            self._sync_cur_size()

        def _drag_update(_g: Gtk.GestureDrag, ox: float, oy: float) -> None:
            if self._mode == "plain":
                return  # the WM's own decorations move the window
            # Ignore sub-threshold jitter so a click isn't treated as a drag.
            if abs(ox) < 3 and abs(oy) < 3 and self._ghost is None:
                return
            # Create the ghost lazily on first real movement.
            if self._ghost is None:
                self._ghost = self._make_ghost(
                    self._cur_w, self._cur_h, self._drag_start[0], self._drag_start[1]
                )
                bar.set_cursor_from_name("grabbing")
            st, sl = self._drag_start
            top = max(0, st + int(oy))
            left = max(0, sl + int(ox))
            self._position_ghost(self._ghost, top, left)

        def _drag_end(_g: Gtk.GestureDrag, ox: float, oy: float) -> None:
            # If no ghost was created, this was a click, not a drag — do nothing.
            if self._ghost is None:
                return
            st, sl = self._drag_start
            self._margin_top = max(0, st + int(oy))
            self._margin_left = max(0, sl + int(ox))
            self._ghost.destroy()
            self._ghost = None
            bar.set_cursor_from_name("grab")
            if self._win is not None:
                if self._mode == "layer":
                    LayerShell.set_margin(self._win, LayerShell.Edge.TOP, self._margin_top)
                    LayerShell.set_margin(self._win, LayerShell.Edge.LEFT, self._margin_left)
                elif self._mode == "x11":
                    xid = get_xid(self._win)
                    if xid:
                        move_window(xid, self._margin_left, self._margin_top)
            self._config.overlay_y = self._margin_top
            self._config.overlay_x = self._margin_left
            with contextlib.suppress(Exception):
                self._config.save()

        drag.connect("drag-begin", _drag_begin)
        drag.connect("drag-update", _drag_update)
        drag.connect("drag-end", _drag_end)
        bar.add_controller(drag)

        # Chat list in a scroller.
        self._list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._list.add_css_class("bc-chat")
        self._scroller = Gtk.ScrolledWindow()
        self._scroller.set_hexpand(True)
        self._scroller.set_vexpand(True)
        self._scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        # Keep the scroller's minimum small so a long chat line can't force the
        # whole window wider/taller than the requested size — otherwise the
        # real window grows past what the resize ghost previewed.
        self._scroller.set_min_content_width(1)
        self._scroller.set_min_content_height(1)
        self._scroller.set_child(self._list)

        # Reply box (always present, click to type).
        reply_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        reply_row.add_css_class("bc-reply")
        self._reply_entry = Gtk.Entry()
        self._reply_entry.set_hexpand(True)
        self._reply_entry.set_placeholder_text(tr("overlay.reply.placeholder"))
        self._reply_entry.connect("activate", self._on_reply_activate)

        # Target-language selector for outgoing replies, next to the input.
        self._reply_lang_dd = Gtk.DropDown(model=Gtk.StringList())
        for code in _REPLY_LANGS:
            self._reply_lang_dd.get_model().append(code)
        try:
            self._reply_lang_dd.set_selected(_REPLY_LANGS.index(self._reply_lang))
        except ValueError:
            self._reply_lang_dd.set_selected(0)
        self._reply_lang_dd.set_cursor_from_name("pointer")
        self._reply_lang_dd.set_tooltip_text(tr("overlay.reply.into"))
        self._reply_lang_dd.connect("notify::selected", self._on_reply_lang_changed)

        reply_row.append(self._reply_entry)
        reply_row.append(self._reply_lang_dd)

        # Result row: translated text + a copy button (clipboard only — the user
        # pastes into the game themselves; the app never sends input to WoW).
        result_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._reply_status = Gtk.Label(label="")
        self._reply_status.set_xalign(0.0)
        self._reply_status.set_hexpand(True)
        self._reply_status.set_wrap(True)
        self._reply_status.set_selectable(True)
        self._copy_btn = Gtk.Button(label=tr("overlay.reply.copy"))
        self._copy_btn.set_cursor_from_name("pointer")
        self._copy_btn.set_sensitive(False)
        self._copy_btn.set_tooltip_text(tr("overlay.reply.copy"))
        self._copy_btn.connect("clicked", self._on_copy_clicked)
        result_row.append(self._reply_status)
        result_row.append(self._copy_btn)
        # Empty status + disabled Copy are dead space — keep the row hidden
        # until a reply translation is in flight or done.
        result_row.set_visible(False)
        self._result_row = result_row
        self._last_reply_text: str = ""

        root.append(bar)
        root.append(self._build_filter_bar())
        root.append(self._scroller)
        root.append(reply_row)
        root.append(result_row)

        # Bottom-right resize grip. Resizing a top-left-anchored layer surface
        # is cleanest from the bottom-right (the anchored corner stays put).
        # Like dragging, live resize would jitter, so we show a ghost outline at
        # the proposed size and commit to the real window on release.
        # Floated over the content via Gtk.Overlay so it doesn't cost a row.
        # Drawn corner bracket instead of a font glyph: glyphs never fill
        # their em box, so a Label can't sit flush in the corner.
        grip = Gtk.DrawingArea()
        grip.set_content_width(16)
        grip.set_content_height(16)
        grip.add_css_class("bc-grip")
        grip.set_tooltip_text(tr("overlay.resize_hint"))
        self._grip = grip
        grip.set_cursor_from_name("nwse-resize")
        grip.set_halign(Gtk.Align.END)
        grip.set_valign(Gtk.Align.END)

        def _draw_grip(area: Gtk.DrawingArea, cr, w: int, h: int) -> None:
            c = area.get_color()  # follows .bc-grip CSS color
            cr.set_source_rgba(c.red, c.green, c.blue, c.alpha)
            cr.set_line_width(2.0)
            # corner bracket: along the bottom edge and up the right edge
            cr.move_to(w * 0.3, h - 1.0)
            cr.line_to(w - 1.0, h - 1.0)
            cr.line_to(w - 1.0, h * 0.3)
            cr.stroke()

        grip.set_draw_func(_draw_grip)

        resize = Gtk.GestureDrag.new()
        self._resize_start: tuple[int, int] = (0, 0)

        def _resize_begin(_g: Gtk.GestureDrag, _sx: float, _sy: float) -> None:
            self._sync_cur_size()
            self._resize_start = (self._cur_w, self._cur_h)

        def _resize_update(_g: Gtk.GestureDrag, ox: float, oy: float) -> None:
            if abs(ox) < 3 and abs(oy) < 3 and self._ghost is None:
                return
            sw, sh = self._resize_start
            new_w = max(_MIN_W, sw + int(ox))
            new_h = max(_MIN_H, sh + int(oy))
            if self._ghost is None:
                self._ghost = self._make_ghost(new_w, new_h, self._margin_top, self._margin_left)
            else:
                # Set the exact size each update. Setting size_request to the
                # exact value (overwritten every tick) lets the ghost both grow
                # and shrink to follow the drag.
                self._ghost.set_size_request(new_w, new_h)
                self._ghost.set_default_size(new_w, new_h)

        def _resize_end(_g: Gtk.GestureDrag, ox: float, oy: float) -> None:
            if self._ghost is None:
                return
            sw, sh = self._resize_start
            self._cur_w = max(_MIN_W, sw + int(ox))
            self._cur_h = max(_MIN_H, sh + int(oy))
            self._ghost.destroy()
            self._ghost = None
            if self._win is not None:
                # To force a mapped window to an exact size (including SHRINKING),
                # set the size request to the exact size, then relax it back to
                # the MIN floor on the next idle so future shrinks remain
                # possible. default_size alone won't shrink an already-mapped
                # window; size_request does, but left pinned it would block the
                # next inward resize.
                w, h = self._cur_w, self._cur_h
                self._win.set_size_request(w, h)
                self._win.set_default_size(w, h)

                def _relax() -> bool:
                    if self._win is not None:
                        self._win.set_size_request(_MIN_W, _MIN_H)
                    return False

                GLib.idle_add(_relax)
            self._config.overlay_width = self._cur_w
            self._config.overlay_height = self._cur_h
            with contextlib.suppress(Exception):
                self._config.save()

        resize.connect("drag-begin", _resize_begin)
        resize.connect("drag-update", _resize_update)
        resize.connect("drag-end", _resize_end)
        grip.add_controller(resize)
        overlay_stack = Gtk.Overlay()
        overlay_stack.set_child(root)
        overlay_stack.add_overlay(grip)
        win.set_child(overlay_stack)

        # Styling: only THIS overlay window's background is made transparent
        # (scoped via the .bc-window class) — using a bare `window` selector
        # would leak to every window in the app (e.g. the settings dialog),
        # making them transparent too. The `.bc-root` rgba then blends against
        # whatever is behind the overlay (the game) for true transparency.
        win.add_css_class("bc-window")
        self._css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            win.get_display(), self._css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self._win = win
        self.apply_appearance()
        import logging
        logging.getLogger(__name__).info(
            "overlay geometry: size=%dx%d (centered, no anchors) opacity=%.2f",
            width, height, opacity,
        )
        win.present()

        # Flush messages queued before the window existed (history + any
        # pipeline messages that arrived during startup).
        if self._pending:
            pending, self._pending = self._pending, []
            for queued in pending:
                self._add_or_update_row(queued)

    # ── reply handling ────────────────────────────────────────────────────
    def set_wow_status_checker(self, checker) -> None:
        """Set a callable returning 'attached' / 'searching' / other and start
        polling it every _WOW_STATUS_INTERVAL seconds."""
        self._wow_checker = checker
        GLib.timeout_add_seconds(_WOW_STATUS_INTERVAL, self._update_wow_status)
        self._update_wow_status()

    def _update_wow_status(self) -> bool:
        checker = getattr(self, "_wow_checker", None)
        label = getattr(self, "_wow_status", None)
        if checker is None:
            return False  # stop polling
        if label is None:
            return True  # window not built yet — keep polling
        try:
            status = checker()
        except Exception:  # noqa: BLE001 — status polling must never crash the UI
            status = "offline"
        for cls in ("bc-wow-ok", "bc-wow-search", "bc-wow-off"):
            label.remove_css_class(cls)
        if status == "attached":
            label.set_label("WoW: \u2714")
            label.add_css_class("bc-wow-ok")
        elif status == "searching":
            label.set_label("WoW: \u2026")
            label.add_css_class("bc-wow-search")
        else:
            label.set_label("WoW: \u2716")
            label.add_css_class("bc-wow-off")
        return True  # keep the GLib timer running

    def toggle_visible(self) -> bool:
        """Show/hide the overlay window; returns the new visibility."""
        if self._win is None:
            return False
        visible = not self._win.get_visible()
        self._win.set_visible(visible)
        if self.on_visibility_changed is not None:
            self.on_visibility_changed(visible)
        return visible

    def set_translation_active(self, enabled: bool) -> None:
        """Set the TR toggle state (fires the normal toggled handler)."""
        if getattr(self, "_translate_toggle", None) is not None:
            self._translate_toggle.set_active(enabled)

    def apply_language(self) -> None:
        """Refresh all persistent overlay UI text after a language change."""
        if self._win is None:
            return
        self._translate_toggle.set_label(
            tr("overlay.badge.on") if self._translate_toggle.get_active() else tr("overlay.badge.off")
        )
        self._translate_toggle.set_tooltip_text(tr("overlay.translate_toggle"))
        self._reply_entry.set_placeholder_text(tr("overlay.reply.placeholder"))
        self._reply_lang_dd.set_tooltip_text(tr("overlay.reply.into"))
        self._copy_btn.set_label(tr("overlay.reply.copy"))
        self._copy_btn.set_tooltip_text(tr("overlay.reply.copy"))
        if self._grip is not None:
            self._grip.set_tooltip_text(tr("overlay.resize_hint"))
        self._update_filter_labels()

    def _update_filter_labels(self) -> None:
        for name, btn in getattr(self, "_filter_buttons", {}).items():
            btn.set_label(tr(_FILTER_LABELS[name]))

    def apply_appearance(self) -> None:
        """(Re)build the overlay CSS from current config — opacity, font size.

        Safe to call live (e.g. after settings Save) to restyle without restart.
        """
        if getattr(self, "_css_provider", None) is None:
            return
        self._theme = resolve_theme(self._config)
        theme = self._theme
        opacity = max(0.1, min(1.0, (self._config.overlay_opacity or 200) / 255.0))
        font_px = max(8, int(self._config.overlay_font_size or 12))
        r, g, b = hex_to_rgb(theme.bg_color)
        family = (self._config.overlay_font_family or "").replace('"', "").strip()
        font_css = f' font-family: "{family}";' if family else ""
        # Text shadow only helps on dark backgrounds; drop it for light themes.
        luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
        shadow = "text-shadow: 0 1px 2px rgba(0,0,0,0.9);" if luma < 128 else ""
        self._css_provider.load_from_data((
            f"window.bc-window {{ background-color: transparent; }}"
            f".bc-root {{ background-color: rgba({r},{g},{b},{opacity:.3f}); padding: 6px;"
            f" border-radius: {theme.corner_radius}px;{font_css} }}"
            f".bc-bar {{ color: #b3b3b3; }}"
            f".bc-filter button {{ padding: 0 6px; min-height: 0; font-size: {max(8, font_px - 2)}px;"
            f" background: rgba(40,40,40,0.6); color: #999999; border: 1px solid #555555;"
            f" border-radius: 3px; box-shadow: none; }}"
            f".bc-filter button:hover {{ color: #cccccc; border-color: #888888; }}"
            f".bc-filter button:checked {{ background: rgba(80,80,80,0.8);"
            f" color: {theme.translation_color}; border-color: {theme.translation_color}; }}"
            f".bc-chat {{ padding: 4px; }}"
            f".bc-chat label {{ {shadow} }}"
            f".bc-grip {{ color: #888888; }}"
            f".bc-wow {{ font-size: {max(8, font_px - 2)}px; padding: 0 4px; color: #888888; }}"
            f".bc-wow-ok {{ color: {theme.tl_on_color}; }}"
            f".bc-wow-search {{ color: {theme.translation_color}; }}"
            f".bc-wow-off {{ color: #888888; }}"
            # Title-bar controls, ported from the PyQt overlay stylesheets.
            f".bc-bar button {{ padding: 0 6px; min-height: 0; font-size: {max(8, font_px - 2)}px;"
            f" border-radius: 3px; box-shadow: none; font-weight: bold; }}"
            f".bc-tl {{ background: {dim(theme.tl_off_color, 0.4)}; color: {theme.tl_off_color};"
            f" border: 1px solid {theme.tl_off_color}; }}"
            f".bc-tl:hover {{ background: {dim(theme.tl_off_color, 0.55)}; }}"
            f".bc-tl:checked {{ background: {dim(theme.tl_on_color, 0.4)}; color: {theme.tl_on_color};"
            f" border-color: {theme.tl_on_color}; }}"
            f".bc-tl:checked:hover {{ background: {dim(theme.tl_on_color, 0.55)}; }}"
            f".bc-tool {{ background: rgba(60,60,60,0.8); color: {theme.tool_color}; border: 1px solid #555555; }}"
            f".bc-tool:hover {{ color: {theme.translation_color}; border-color: {theme.translation_color}; }}"
            f".bc-close {{ background: {dim(theme.close_color, 0.4)}; color: {theme.close_color};"
            f" border: 1px solid {theme.close_color}; }}"
            f".bc-close:hover {{ background: {dim(theme.close_color, 0.55)}; }}"
            f".bc-reply entry {{ font-size: {font_px}px; }}"
        ).encode())
        # Restyle already-visible messages so theme changes apply instantly.
        for row in self._rows.values():
            row.restyle(font_px, theme)

    def _build_filter_bar(self) -> Gtk.Widget:
        # Horizontal scroller so the tabs don't force the overlay wider.
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        bar.add_css_class("bc-filter")
        self._filter_buttons: dict[str, Gtk.ToggleButton] = {}
        first: Gtk.ToggleButton | None = None
        for name in _FILTER_ORDER:
            btn = Gtk.ToggleButton(label=tr(_FILTER_LABELS[name]))
            if first is None:
                first = btn
            else:
                btn.set_group(first)  # radio behavior: only one active
            btn.set_active(name == self._active_filter)
            btn.connect("toggled", self._on_filter_toggled, name)
            btn.set_cursor_from_name("pointer")
            self._filter_buttons[name] = btn
            bar.append(btn)
        scroller.set_child(bar)
        return scroller

    def _on_filter_toggled(self, btn: Gtk.ToggleButton, name: str) -> None:
        if not btn.get_active():
            return  # only react to the newly-activated button
        self._active_filter = name
        self._apply_filter()

    def _apply_filter(self) -> None:
        if self._list is None:
            return
        allowed = _FILTER_CHANNELS.get(self._active_filter, set(Channel))
        child = self._list.get_first_child()
        while child is not None:
            if isinstance(child, _MessageRow):
                child.set_visible(child.channel in allowed)
            child = child.get_next_sibling()
        self._scroll_to_bottom()

    def _on_translate_toggled(self, btn: Gtk.ToggleButton) -> None:
        active = btn.get_active()
        btn.set_label(tr("overlay.badge.on") if active else tr("overlay.badge.off"))
        if self.on_toggle_translation is not None:
            self.on_toggle_translation(active)

    def _on_reply_activate(self, entry: Gtk.Entry) -> None:
        text = entry.get_text().strip()
        if not text:
            return
        entry.set_text("")
        if self._reply_status is not None:
            if getattr(self, "_result_row", None) is not None:
                self._result_row.set_visible(True)
            self._reply_status.set_markup(
                f'<span foreground="#cccc66">{tr("overlay.reply.translating")}</span>'
            )
        # Translate off the GTK main thread so the UI doesn't freeze.
        threading.Thread(
            target=self._translate_reply_worker, args=(text,), daemon=True
        ).start()

    def _translate_reply_worker(self, text: str) -> None:
        result_text = text
        ok = False
        if self._translator is not None:
            try:
                res = self._translator.translate(text, self._reply_lang)
                if res.success:
                    result_text = res.translated
                    ok = True
            except Exception as exc:  # noqa: BLE001
                result_text = f"error: {exc}"
        GLib.idle_add(self._show_reply_result, result_text, ok)

    def _on_reply_lang_changed(self, dd: Gtk.DropDown, _param: object) -> None:
        idx = dd.get_selected()
        if 0 <= idx < len(_REPLY_LANGS):
            self._reply_lang = _REPLY_LANGS[idx]

    def _on_copy_clicked(self, _btn: Gtk.Button) -> None:
        if not self._last_reply_text:
            return
        # Clipboard only — user pastes into WoW themselves.
        clipboard = self._copy_btn.get_clipboard()
        clipboard.set(self._last_reply_text)
        self._copy_btn.set_label(tr("overlay.reply.copied"))
        def _reset() -> bool:
            self._copy_btn.set_label(tr("overlay.reply.copy"))
            return False
        GLib.timeout_add_seconds(1, _reset)

    def _show_reply_result(self, result_text: str, ok: bool) -> bool:
        if self._reply_status is not None:
            color = "#99ff99" if ok else "#ff8080"
            self._reply_status.set_markup(
                f'<span foreground="{color}">{GLib.markup_escape_text(result_text)}</span>'
            )
        if ok:
            self._last_reply_text = result_text
            if getattr(self, "_copy_btn", None) is not None:
                self._copy_btn.set_sensitive(True)
            if self.on_reply_send is not None:
                self.on_reply_send(result_text)
        return False
