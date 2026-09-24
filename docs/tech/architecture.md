# Architecture Overview

## System Design

BabelChat is a two-component system: a WoW addon (Lua) captures chat messages, and a companion app (Python) translates them.

```
WoW Process                          Companion App (Python, no elevation)
┌─────────────────────┐              ┌──────────────────────────────┐
│  BabelChat addon    │              │  Memory Reader               │
│  ├── ChatFilter     │  pointer     │  ├── Anchor → slot → buffer  │
│  ├── Ring buffer    │──from the──→ │  ├── Pulse: is this copy     │
│  ├── DictEngine     │  addon's     │  │   still being written to? │
│  │   + anchor+pulse │  table       │  └── Sweep, only as fallback │
│  └── SavedVariable  │  (250ms)     │          │                   │
│      BabelChatDB    │              │          ▼                   │
└─────────────────────┘              │  Pipeline                    │
                                     │  ├── Parse → Dedup → Filter  │
                                     │  ├── Detect language          │
                                     │  ├── Phrasebook (instant)     │
                                     │  ├── Cache (SQLite + LRU)     │
                                     │  ├── Provider chain (0.5-2s)  │
                                     │  └── Streaming emit           │
                                     │          │                   │
                                     │          ▼                   │
                                     │  Overlay (PyQt6 / GTK4)      │
                                     │  ├── Channel colors           │
                                     │  ├── Click-through            │
                                     │  └── Progressive rendering    │
                                     └──────────────────────────────┘
```

## Data Flow

1. WoW fires `CHAT_MSG_*` event → addon's `ChatFilter` intercepts
2. Addon writes `SEQ|KIND|EVENT|author|text` to ring buffer (50 entries)
3. Every 0.25s (`FLUSH_INTERVAL` in `CompanionBuffer.lua`, matched to the companion's poll rate), the addon flushes the buffer to `BabelChatDB.wctbuf` (Lua SavedVariable string)
4. Companion reads the buffer every 250ms — through a pointer the addon parks
   for it, not by searching. See [memory-reader.md](memory-reader.md): a Lua
   string is reallocated somewhere new on every rebuild, so searching costs a
   sweep of the heap per rebuild, which is 48% of one core, measured.
5. Parser extracts messages, dedup filters duplicates (60s TTL, monotonic clock)
6. Language detector (lingua-py, offline) identifies source language
7. Translation stages (abbreviations → phrasebook → cache → slang expansion → WoW terms → provider chain)
8. **Streaming**: original message emitted immediately, translation update follows when the provider responds
9. Overlay renders with channel colors, updates in-place on translation arrival

## Translation Providers

Four providers register themselves at import of `app.translators`. The listing
and fall-through order is set there, once: **gigachat, mymemory, deepl,
microsoft**. `AppConfig.translator_priority` defaults to `gigachat`.

The order is not a quality ranking. GigaChat leads because it is the only one of
the four reachable from Russia without a VPN or a foreign card; MyMemory follows
because it needs no account at all, so `TranslatorService` adds it even when the
config does not mention it — that is what makes translation work on a fresh
install before anything is configured. `TranslatorService` tries the preferred
provider first and falls through the rest on failure or quota.

Adding a provider means one `ProviderSpec` (id, display name, credential fields,
`build`, `validate`) and nothing else: both settings dialogs and both wizards
render whatever the registry holds.

## Module Map (54 modules, ~13,500 LOC)

Run `wc -l app/*.py app/translators/*.py` before trusting this table. The larger
modules, and every module the rest of this document names:

| Module | Lines | Purpose |
|--------|-------|---------|
| `i18n` | ~1,260 | RU/EN/ES UI localization (all strings) |
| `overlay_gtk` | ~1,030 | Linux overlay: layer-shell, X11 and plain modes |
| `overlay` | ~580 | Windows overlay window: behaviour, rendering, streaming updates |
| `phrasebook` | ~510 | 53 phrases + 75 abbreviations (EN, RU, DE, FR, ES) |
| `setup_wizard` | ~460 | First-run wizard, PyQt (5 steps) |
| `settings_gtk` | ~440 | Linux settings window |
| `pipeline` | ~440 | Translation orchestration with streaming |
| `memory_reader_windows` | ~350 | Poll loop, sequence tracking, and what to tell the user when nothing arrives |
| `parser` | ~430 | WoW chat log parser (EN+RU clients, addon record format) |
| `settings_dialog` | ~430 | Windows settings UI (tabs: General, Overlay, Hotkeys, About) |
| `translators/gigachat_provider` | ~400 | GigaChat backend: it is an LLM, so the request is a chat completion pinned to translating |
| `main` | ~400 | Windows entry point, single-instance guard, logging |
| `config` | ~390 | Config JSON, atomic save, migrations, channel toggle table |
| `tray_sni` | ~390 | Linux tray icon over the StatusNotifierItem D-Bus spec |
| `setup_wizard_gtk` | ~370 | First-run wizard, GTK |
| `memory_reader_linux` | ~330 | `process_vm_readv` via the Rust scanner |
| `provider_settings_qt` | ~290 | Credential fields rendered from the provider registry |
| `translators/base` | ~285 | `ProviderSpec`, registry, retry policy, result types |
| `overlay_chrome` | ~280 | Building that window's furniture — title bar, toolbar, chat area, reply row |
| `overlay_theme` | ~250 | Overlay colour presets (read by the GTK frontend) |
| `overlay_reply` | ~250 | The reply box, and the clipboard hand-off that keeps it out of automation |
| `addon_protocol` | ~220 | The record format and channel classification, shared by both readers |
| `translators/mymemory_provider` | ~205 | Keyless fallback backend |
| `main_gtk` | ~205 | Linux entry point |
| `overlay_widgets` | ~205 | Resize grip, channel filter bar, reply translation worker, channel colours |
| `glossary_data` | ~200 | Pirson's WoW glossary (80 abbreviations, 102 expansions) |
| `cache` | ~180 | Two-level: LRU + SQLite (7-day TTL), thread-safe |
| `translators/deepl_provider` | ~155 | DeepL backend |
| `translators/microsoft_provider` | ~140 | Microsoft Translator backend |
| `detector` | ~135 | Language detection + Cyrillic fallback for short text |
| `x11_window` | ~135 | EWMH always-on-top and positioning for the X11 overlay mode |
| `hotkeys_windows` / `hotkeys_linux` | ~120 each | Global hotkeys per platform, behind the `hotkeys` dispatcher |
| `translators/service` | ~110 | Picks a provider, falls through to the next on failure |
| `native_scanner` | ~110 | ctypes binding to the Rust scanner library |
| `watcher` | ~105 | File watcher fallback (polls WoWChatLog.txt) |
| `glossary` | ~90 | WoW abbreviation lookup + context-gated expansion |
| `slang` | ~85 | Gaming slang normalizer before the provider call |
| `text_utils` | ~80 | URL stripping, token preservation, color code removal |
| `translator` | ~55 | Re-export shim: the import path the rest of the app uses |
| `memory_reader`, `hotkeys` | ~25, ~10 | Platform dispatchers |

## Threading Model

| Thread | Owns | Writes to |
|--------|------|-----------|
| Main (PyQt6 or GTK4 event loop) | Overlay, Settings, Tray | `_config` via `update_config()` |
| Memory reader | `WoWAddonBufReader._run_loop` | Calls `pipeline._on_new_line` |
| File watcher (fallback) | `ChatLogWatcher._poll_loop` | Calls `pipeline._on_new_line` |
| Rust scanner | Anchor lookup and, failing that, the region sweep | Return values only (no shared state) |

**Thread safety:**
- `_recent_messages` protected by `threading.Lock`
- `_config` access uses snapshot (`cfg = self._config`) for consistent reads
- `TranslationCache` protected by `threading.Lock`
- Qt signals (`message_received`) for cross-thread overlay updates
- `_next_msg_id` incremented under lock

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Memory buffer, not file watcher | WoW buffers WoWChatLog.txt by volume, and chat is low volume — minutes of delay. Through memory: one poll |
| Overlay, not in-game UI | WoW Lua sandbox cannot make HTTP requests. An external overlay can call a translation API |
| Streaming translation | Show original immediately (0ms), translation arrives async (0.5-2s). Perceived latency = 0 |
| Outgoing via clipboard | No automation — the app never sends chat; the user pastes it |
| Python, with Rust where it counts | The reading is I/O-bound and Python is fine for it; finding the buffer is not, and that part is a Rust cdylib. Python gives PyQt6/GTK4, lingua-py and the provider SDKs |
| GigaChat first in the chain | Reachability, not quality: no card, no VPN, free for individuals. MyMemory second because it needs no account at all |
| MIT license | Compatible with Pirson's WoW Translator (MIT), simplest for community |

## Tests

795 tests in 30 files — `QT_QPA_PLATFORM=offscreen python -m pytest -q`.
The addon's Lua is exercised under a real Lua 5.1 interpreter through `lupa`
(`tests/lua_harness.py`), so the Lua in `addon/` is tested from Python rather
than re-implemented in it.

- Engine: `test_cache.py`, `test_dedup.py`, `test_parser.py`,
  `test_phrasebook.py`, `test_glossary.py`, `test_text_utils.py`,
  `test_pipeline.py`, `test_channel_classification.py`
- Providers: `test_translator_registry.py`, `test_translator_gigachat.py`,
  `test_translator_mymemory.py`, `test_gigachat_credential.py`
- Addon: `test_addon_toc_and_libs.py`, `test_addon_dict_engine.py`,
  `test_addon_dict_corpus.py`, `test_addon_dict_locales.py`,
  `test_addon_companion_buffer.py`, `test_addon_companion_contract.py`,
  `test_addon_commands.py`, `test_addon_config_settings.py`,
  `test_dict_coverage.py`
- UI and packaging: `test_i18n_completeness.py`, `test_settings_layout.py`,
  `test_overlay_theme.py`, `test_hotkeys_wired.py`, `test_native_scanner.py`,
  `test_config_upgrade.py`, `test_debug_log_privacy.py`,
  `test_release_workflow.py`, and `test_tray_sni.py`, which needs PyGObject and
  skips where it is absent

`test_addon_toc_and_libs.py` also guards this document: a term count or a
category count that does not match the data files fails the suite, as does any
line that tells the user to elevate — the build stopped asking for elevation.
