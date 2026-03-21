# WoW Addon Internals

## Structure

```
addon/BabelChat/
├── BabelChat.toc       # Manifest: version, load order, SavedVariables
├── Core.lua            # Initialization, chat filter, slash commands, welcome frame
├── DictEngine.lua      # Dictionary translation engine (annotation-based)
├── CompanionBuffer.lua # Ring buffer for companion app (ReadProcessMemory)
├── Config.lua          # Settings UI panel (Interface > AddOns > BabelChat)
├── Locales.lua         # UI strings (EN, RU, ES)
├── Data/               # 12 dictionary files (347 terms × 14 languages)
├── Libs/               # Embedded libraries (LibStub, LibBabble, LibDBIcon, etc.)
└── img/logo_wt.tga     # Addon icon
```

## Chat Filter (Core.lua)

BabelChat hooks all chat events via `ChatFrame_AddMessageEventFilter`:

```lua
ChatFrame_AddMessageEventFilter(event, ChatFilter)
```

The `ChatFilter` function:
1. Runs dictionary translation if enabled → produces annotation
2. Writes to companion buffer (ALL channels, regardless of dict filter)
3. Returns modified text (annotation below original) for in-game display

## Ring Buffer (CompanionBuffer.lua)

- 50-message ring buffer with dedup (author+text, 2s TTL)
- Format: `SEQ|KIND|EVENT|author|text` (tab separator for DICT translated text)
- Flushed to `BabelChatDB.wctbuf` every 1.5s via `C_Timer.NewTicker`
- Pre-allocated SavedVariable keys for pointer stability
- `pcall` wrapping for secret-tainted instance chat

## Dictionary Engine (DictEngine.lua)

Based on Pirson's WoW Translator (MIT License), rewritten for v2:

- **Annotation-based** (not inline replacement): `→ term1, term2`
- **Hyperlink-aware**: skips `|H...|h` and `|cff...|r` blocks
- **Overlap guard**: matched ranges tracked, no double translations
- **Multi-word priority**: longest phrases matched first
- **12 categories**: Social, Classes, Combat, Raid, Groups, Stats, Professions, Trade, Status, Guild, Roles, Slang

## Config UI (Config.lua)

WoW settings panel with sections:
- General: enable/disable, translation color picker
- Categories: 12 toggles for dictionary categories
- Channels: 7 channel type toggles
- Language: 14-language dropdown
- Companion: enable/disable companion buffer
- Mode: Dictionary only / Overlay only / Both

## Slash Commands

| Command | Action |
|---------|--------|
| `/babel` | Show help |
| `/babel config` | Open settings |
| `/babel on/off` | Toggle dictionary |
| `/babel test` | Test with sample message |
| `/babel companion` | Buffer status |
| `/babel poll on/off` | Toggle GetMessageInfo fallback |
| `/babel log on/off` | Toggle chat file logging |

## SavedVariables

`BabelChatDB` stores:
- `dict.*` — dictionary settings (enabled, locale, color, category toggles, channel toggles)
- `companion.*` — companion app settings (enabled, flush interval)
- `minimap.*` — minimap icon position
- `wctbuf` — ring buffer content (read by companion app)
- `wctSeq` — sequence counter (persists across `/reload`)

## Migration

On first load, if `ChatTranslatorHelperDB` exists (old addon name), settings are automatically migrated to `BabelChatDB`.
