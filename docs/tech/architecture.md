# Architecture Overview

## System Design

BabelChat is a two-component system: a WoW addon (Lua) captures chat messages, and a companion app (Python) translates them.

```
WoW Process                          Companion App (Python, admin)
┌─────────────────────┐              ┌──────────────────────────────┐
│  BabelChat addon    │              │  Memory Reader               │
│  ├── ChatFilter     │  ReadProc    │  ├── Tiered scan cascade     │
│  ├── Ring buffer    │──Memory───→  │  ├── Seq freshness tracking  │
│  ├── DictEngine     │  (250ms)     │  └── Zombie buffer detection │
│  └── SavedVariable  │              │          │                   │
│      BabelChatDB    │              │          ▼                   │
└─────────────────────┘              │  Pipeline                    │
                                     │  ├── Parse → Dedup → Filter  │
                                     │  ├── Detect language          │
                                     │  ├── Phrasebook (instant)     │
                                     │  ├── Cache (SQLite + LRU)     │
                                     │  ├── DeepL API (0.5-2s)       │
                                     │  └── Streaming emit           │
                                     │          │                   │
                                     │          ▼                   │
                                     │  Overlay (PyQt6)             │
                                     │  ├── Channel colors           │
                                     │  ├── Click-through            │
                                     │  └── Progressive rendering    │
                                     └──────────────────────────────┘
```

## Data Flow

1. WoW fires `CHAT_MSG_*` event → addon's `ChatFilter` intercepts
2. Addon writes `SEQ|KIND|EVENT|author|text` to ring buffer (50 entries)
3. Every 1.5s, addon flushes buffer to `BabelChatDB.wctbuf` (Lua SavedVariable string)
4. Companion app reads buffer via `ReadProcessMemory` every 250ms
5. Parser extracts messages, dedup filters duplicates (60s TTL, monotonic clock)
6. Language detector (lingua-py, offline) identifies source language
7. Translation stages (phrasebook → cache → slang expansion → WoW terms → DeepL)
8. **Streaming**: original message emitted immediately, translation update follows when DeepL responds
9. Overlay renders with channel colors, updates in-place on translation arrival

## Module Map (23 modules, ~7,500 LOC)

| Module | Lines | Purpose |
|--------|-------|---------|
| `memory_reader` | ~900 | ReadProcessMemory, tiered scan, seq tracking, zombie detection |
| `settings_dialog` | ~900 | Settings UI (tabs: General, Languages, Channels, About + donations) |
| `overlay` | ~870 | Smart overlay (WoW-themed, channel colors, streaming updates) |
| `setup_wizard` | ~670 | First-run wizard (5 steps) |
| `phrasebook` | ~510 | 45 phrases + 30 abbreviations (EN, RU, DE, FR, ES) |
| `parser` | ~490 | WoW chat log parser (EN+RU clients, addon v2.1 format) |
| `i18n` | ~940 | RU/EN/ES UI localization (all strings) |
| `pipeline` | ~410 | Translation orchestration with streaming |
| `main` | ~310 | Entry point, single-instance guard, logging |
| `glossary_data` | ~200 | Pirson's WoW glossary (80 abbreviations, 102 expansions) |
| `about_dialog` | ~170 | About tab with version, credits, donations |
| `reply_widget` | ~160 | Outgoing translator (clipboard-based) |
| `cache` | ~150 | Two-level: LRU (1000 entries) + SQLite (7-day TTL), thread-safe |
| `detector` | ~140 | Language detection + Cyrillic fallback for short text |
| `translator` | ~140 | DeepL API wrapper with retry, timeout, exception fallback |
| `config` | ~125 | Config JSON, atomic save, .bak backup, WoW path detection |
| `hotkeys` | ~120 | Global hotkey manager (RegisterHotKey) |
| `watcher` | ~105 | File watcher fallback (polls WoWChatLog.txt) |
| `tray` | ~100 | System tray icon |
| `glossary` | ~90 | WoW abbreviation lookup + context-gated expansion |
| `slang` | ~85 | Gaming slang normalizer for DeepL |
| `lang_selector` | ~85 | Language dropdown widget |
| `text_utils` | ~70 | URL stripping, token preservation, color code removal |

## Threading Model

| Thread | Owns | Writes to |
|--------|------|-----------|
| Main (PyQt6 event loop) | Overlay, Settings, Tray | `_config` via `update_config()` |
| Memory reader | `WoWAddonBufReader._run_loop` | Calls `pipeline._on_new_line` |
| File watcher (fallback) | `ChatLogWatcher._poll_loop` | Calls `pipeline._on_new_line` |
| ThreadPoolExecutor (8) | Parallel heap scan | Return values only (no shared state) |

**Thread safety:**
- `_recent_messages` protected by `threading.Lock`
- `_config` access uses snapshot (`cfg = self._config`) for consistent reads
- `TranslationCache` protected by `threading.Lock`
- Qt signals (`message_received`) for cross-thread overlay updates
- `_next_msg_id` incremented under lock

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Memory buffer, not file watcher | WoW buffers WoWChatLog.txt with 1-5 min delay. Addon → Lua string → ReadProcessMemory = <1s |
| Overlay, not in-game UI | WoW Lua sandbox cannot make HTTP requests. External overlay can call DeepL |
| Streaming translation | Show original immediately (0ms), translation arrives async (0.5-2s). Perceived latency = 0 |
| Outgoing via clipboard | ToS compliance — no automation, user manually pastes |
| Python, not C++/Rust | Bottleneck is I/O (ReadProcessMemory), not CPU. Python gives PyQt6 + lingua-py + DeepL SDK |
| MIT license | Compatible with Pirson's WoW Translator (MIT), simplest for community |

## Tests

133 tests across 6 files:
- `test_cache.py` — thread-safe cache, LRU eviction, TTL, concurrent access
- `test_glossary.py` — abbreviation lookup, context-gated expansion, data integrity
- `test_parser.py` — channel parsing, whispers, edge cases, Unicode, addon v2.1 format
- `test_phrasebook.py` — multilingual lookup, abbreviations, normalization
- `test_pipeline.py` — E2E with mock DeepL: phrasebook, cache, streaming, dedup, filtering
- `test_text_utils.py` — URL stripping, token preservation, color code removal
