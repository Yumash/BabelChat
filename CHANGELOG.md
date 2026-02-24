# Changelog / История изменений

## [1.0.8] — 2026-02-24

### Fixed / Исправлено
- Short phrases "hi", "sup", "go" now translated via phrasebook (were silently skipped due to MIN_TEXT_LENGTH and _SKIP_PHRASES filters)
- Removed "go" from detector skip list — now handled as abbreviation before detection
- Added "hi" → "привет", "sup" → "привет", "go" → "вперёд" as pre-detection abbreviations

## [1.0.7] — 2026-02-23

### Added / Добавлено
- WoW glossary: 80 safe abbreviations (9 languages) from Pirson's WoW Translator addon — instant translation of terms like aoe, dk, ilvl, gz, cc without API call
- Context-gated term expansion: 102 WoW-specific terms (dungeon names, specs, roles) expanded to plain English before DeepL when 2+ gaming terms detected in message
- Safety set: ~40 common English words (add, hit, focus, fire, arms, etc.) excluded from expansion to prevent false positives

### Fixed / Исправлено
- Overlay resize grip now works — bottom-right corner ⇡ icon is a real drag handle
- Reply translator defaults to → EN when own language is RU (was incorrectly set to → RU)
- "go?" no longer mistranslated by DeepL — added to phrasebook as "вперёд"

### Improved / Улучшено
- Memory reader: seq reset guard — prevents re-translation of already-seen messages after addon /reload (saves DeepL API quota)
- Memory reader: exponential backoff for marker-gone detection (2→4→8→16 stale reads before rescan instead of fixed 2)
- Memory reader: adaptive rescan interval (2s→5s→10s→30s) when buffer address is stable, resets to 2s on new messages
- Language detector: short Cyrillic text misdetected as Bulgarian/Ukrainian now treated as Russian (for RU users)
- NPC filter: Say/Yell messages from NPC names (containing spaces) are now filtered from overlay

## [1.0.6] — 2026-02-23

### Fixed / Исправлено
- Fixed duplicate messages flooding overlay — file watcher no longer runs alongside memory reader; WoW buffers chatlog writes for minutes then flushes a huge batch that bypassed dedup TTL
- File watcher now only activates as fallback when memory reader is unavailable (no pymem, no admin rights, WoW not running)

## [1.0.5] — 2026-02-23

### Fixed / Исправлено
- Fixed garbled binary characters (null bytes, raw memory data) appearing in translated messages — GetMessageInfo() can return strings with embedded \x00 bytes from taint corruption; now truncated at first null byte in both addon and companion
- Addon: pcall-wrapped string.find for null byte detection (safe on secret values)
- Companion: defensive payload sanitization strips null bytes and trailing control characters
- Parser: fixed `_is_item_link_only` to match color-stripped hyperlinks — item-link-only messages now correctly filtered

## [1.0.4] — 2026-02-22

### Fixed / Исправлено
- Addon: fixed `table.concat` crash on secret-tainted strings in RebuildBuffer — now pcall-filters each entry individually, skipping secret values
- Addon: concatenation with secret string produces secret result — `wctSeq .. "|RAW|" .. text` stays tainted, now handled gracefully

### Added / Добавлено
- Phrasebook: "zug zug" (orc greeting), "zamn" (slang for damn)
- Slang normalizer: "zamn" → "damn"

## [1.0.3] — 2026-02-22

### Fixed / Исправлено
- Parser: fixed "Parse returned None" for all messages — raw WoW color codes (`|cXXXXXXXX...|r`) inside player names now stripped before regex matching
- Parser: added support for `[BracketChannel] |Hplayer:...|h[Name]|h: text` format (used by Raid Warning / Объявление рейду in RU scrollback)
- Parser: added "Объявление рейду" (dative case) to channel map — RU scrollback uses dative, not genitive
- Addon: removed all dedup logic — secret string taint prevents even table indexing on concat results; companion handles dedup
- Debug console: now toggleable at runtime via Settings without restart; fixed idempotent initialization

## [1.0.2] — 2026-02-22

### Fixed / Исправлено
- Addon: fixed taint error "attempt to compare secret string" in TWW — Secret Values from GetMessageInfo are now concatenated (allowed) instead of compared (forbidden); double pcall contains taint per-frame and per-message
- Addon: removed StripMarkup on addon side — raw text with WoW markup sent to companion, companion parser handles markup stripping
- Pipeline: unmapped lingua languages (e.g. Tswana for "okay alr") now fall through to DeepL auto-detect instead of being skipped

### Added / Добавлено
- Slang normalizer: gaming slang expanded to plain English before DeepL (summ→summon, bio→break, rezz→resurrect, pls→please, etc.) — dramatically improves translation of short chat messages
- DeepL context parameter: "World of Warcraft raid group chat" hint (free, not billed)
- Phrasebook: 30+ new raid abbreviations (summ, bio, rez, cds, bl, hero, brez, wipe, kick, gl guys, gg wp, etc.)
- Version shown in overlay title bar
- "About" tab in settings with developer info, GitHub link, and donate addresses

## [1.0.1] — 2026-02-22

### Fixed / Исправлено
- Undetectable language now falls through to DeepL auto-detect instead of being skipped
- Debug console now works correctly in windowed .exe (AllocConsole + CONOUT$ redirect)
- Console hidden by default — enable via Settings → Overlay → "Show debug console"
- Added INFO-level logging for translation pipeline steps (detect, skip, translate, DeepL result)
- Fixed StreamHandler crash when sys.stderr is None in windowed exe

## [1.0.0] — 2026-02-22

First public release.

Первый публичный релиз.

### Added / Добавлено

**Core / Ядро:**
- Real-time chat translation via addon memory buffer (< 1s latency)
- Tiered memory scanning: region history (~30ms) → heap scan (~2.5s) → full scan (~7s)
- File watcher fallback — polls WoWChatLog.txt every 1s when addon unavailable
- Deduplication — messages from memory reader and file watcher are deduplicated by (author, text) with 30s TTL
- WoW item/spell link filtering — messages with only item links are skipped

**Translation / Перевод:**
- DeepL Free API integration (500K characters/month)
- Built-in phrasebook: 45 phrases (EN/RU/DE/FR/ES) + 30 gaming abbreviations — instant, no API needed
- Two-level translation cache: in-memory LRU (1000 entries) + SQLite persistent cache (7-day TTL)
- Offline language detection via lingua-py (~1ms per message)
- Cyrillic script fallback for short text that lingua can't classify
- Dual-threshold language detector: lenient (0.1) for short text (≤20 chars), strict (0.25) for longer text
- Gaming jargon auto-skip: lol, afk, brb, pull, cc, dps, heal, tank, etc.

**Overlay / Оверлей:**
- Smart overlay with WoW-native dark theme and channel colors
- Click-through mode by default (clicks pass through to the game)
- Draggable title bar, resizable from all edges
- Minimize to title bar with one click
- Channel filter tabs: All, Party, Raid, Guild, Say, Whisper, Instance
- Reply translator panel: type → translate → copy → paste in WoW
- WoW connection status indicator (attached / searching / offline)
- Translation ON/OFF toggle in title bar
- Opacity slider (20-100%)

**WoW Addon / Аддон WoW:**
- ChatTranslatorHelper addon (~300 lines Lua)
- ChatFrame scrollback polling every 200ms
- Ring buffer (50 messages) with `__WCT_BUF__` / `__WCT_END__` markers
- StripMarkup preserves hyperlinks while removing color codes
- `/wct` slash commands: status, buf, log, auto, flush, poll, verbose
- Auto-enable chat logging on login
- Buffer flush every 1.5 seconds

**Configuration / Настройка:**
- 5-step setup wizard for first-time configuration
- Settings dialog with 3 tabs: General, Overlay, Hotkeys
- Global hotkeys via Win32 API (default: Ctrl+Shift+T to toggle translation)
- 22 target languages supported
- One-click addon installation from settings
- Auto-detect WoW path via Windows Registry
- Debug console toggle in settings

**Infrastructure / Инфраструктура:**
- System tray integration with context menu
- PyInstaller single-file .exe build (admin privileges required)
- GitHub Actions: CI (lint + test) and Release (build .exe + GitHub Release)
- Apache-2.0 license
