<p align="center">
  <img src="assets/icon.png" alt="BabelChat" width="80" />
</p>

<h1 align="center">BabelChat</h1>

<p align="center">
  <b>Break the language barrier in World of Warcraft</b><br>
  Real-time chat translation with a smart overlay — companion app + WoW addon
</p>

<p align="center">
  <a href="README_ru.md">Русская версия</a> |
  <a href="README_es.md">Versión en español</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License" /></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.12+-yellow.svg" alt="Python" /></a>
  <a href="https://github.com/Yumash/BabelChat/releases"><img src="https://img.shields.io/github/v/release/Yumash/BabelChat?include_prereleases" alt="Release" /></a>
</p>

<p align="center">
  <a href="https://buymeacoffee.com/franciscorb"><img src="https://img.shields.io/badge/Pirson_(Dictionary)-Buy_Me_a_Coffee-yellow?style=for-the-badge&logo=buymeacoffee&logoColor=white" alt="Buy Me a Coffee" /></a>
  &nbsp;
  <a href="https://yumatech.ru/donate/"><img src="https://img.shields.io/badge/Donate-USDT%20%7C%20OpenCollective-blue?style=for-the-badge&logo=tether&logoColor=white" alt="Donate" /></a>
</p>

---

<p align="center">
  <img src="assets/demo.webp" alt="BabelChat Demo" width="700" />
</p>

## The Problem

You join a PUG raid. The tank explains tactics — in Spanish. The healer asks something — in German. You speak English (or Russian, or French). Nobody understands each other. The pull happens, people die, and someone types "gg noob" — the only phrase everyone knows.

**This happens constantly** in WoW's cross-realm and cross-region groups. Language barriers ruin coordination, cause wipes, and make the game less fun.

## The Solution

BabelChat translates WoW chat **in real time**. A tiny addon captures messages directly from the game; a companion app translates them via DeepL and shows results in a sleek overlay on top of WoW.

**You see the original message instantly. The translation appears 0.5–2 seconds later.**

Common phrases like "gg", "ty", "ready?", "pull" translate instantly from a built-in phrasebook — no API call, no delay. Full sentences go through DeepL and arrive within 1–2 seconds. The same message is never translated twice (cached).

### When is BabelChat useful?

- **Cross-realm PUGs** — understand the Spanish tank's tactics, the German healer's callouts
- **International guilds** — follow guild chat in your language without asking "english pls"
- **Playing on foreign servers** — joined a French or Korean realm? Chat is now readable
- **Raid leading** — give commands in your language, players see them in theirs (via outgoing translator)
- **Whispers from strangers** — understand that random whisper in Portuguese

## Key Features

- **Streaming translation** — original appears instantly, translation follows 0.5–2s later
- **Auto language detection** — offline, ~1ms per message (lingua-py)
- **22 target languages** — EN, RU, DE, FR, ES, IT, PT, PL, NL, SV, DA, FI, CS, RO, HU, BG, EL, TR, UK, JA, KO, ZH
- **Smart overlay** — WoW-themed dark UI, proper channel colors, click-through, draggable
- **Bidirectional** — translate incoming chat AND compose outgoing messages in any language
- **Built-in phrasebook** — 45 phrases + 30 gaming abbreviations translated instantly without API
- **WoW glossary** — 314 gaming terms (lfm, wts, dps, tank, etc.) in 14 languages
- **Channel filters** — Party, Raid, Guild, Say/Yell, Whisper, Instance
- **DeepL Free API** — 500,000 characters/month free (~10K messages)
- **Translation cache** — thread-safe SQLite + LRU, same text never translated twice
- **Global hotkeys** — toggle translation without leaving the game
- **One-click addon install** — setup wizard handles everything

## Why Does Translation Take 0.5–2 Seconds?

BabelChat uses **progressive rendering** (streaming):

1. **You see the original message immediately** (0ms delay)
2. **Translation appears below it** when DeepL responds (0.5–2s)

The delay comes from the DeepL API round-trip — your text travels to DeepL's servers, gets translated by a neural network, and comes back. This is the same latency as Google Translate or any cloud translation service.

**What's instant (no delay):**
- Gaming abbreviations: `gg`, `ty`, `brb`, `afk`, `wp`, `lol` — translated from built-in phrasebook
- Common phrases: "hello", "thanks", "ready?", "good game" — phrasebook
- Repeated messages — served from cache
- Messages in your own language — shown without translation

**What takes 0.5–2s:**
- Full sentences in foreign languages — DeepL API call required
- First occurrence of any phrase — subsequent ones are cached

## How It Works

```
┌──────────────────────────────────────────────────────────┐
│  World of Warcraft                                       │
│                                                          │
│  BabelChat addon                                         │
│  ├── Hooks CHAT_MSG_* events via standard WoW API        │
│  ├── Ring buffer (50 messages)                           │
│  └── Writes to BabelChatDB.wctbuf (Lua SavedVariable)   │
└──────────┬───────────────────────────────────────────────┘
           │  ReadProcessMemory (every 250ms)
           ▼
┌──────────────────────────────────────────────────────────┐
│  Companion App (Python, runs as admin)                   │
│                                                          │
│  Memory Reader ──→ Parser ──→ Language Detector          │
│       │                           │                      │
│       │    Phrasebook (instant) ──┤                      │
│       │    Cache (instant)  ──────┤                      │
│       │    DeepL API (0.5-2s) ────┤                      │
│       │                           ▼                      │
│       └───────────────→ Smart Overlay (PyQt6)            │
└──────────────────────────────────────────────────────────┘
```

### Why a companion app (not just an addon)?

WoW's Lua sandbox **cannot make HTTP requests**. The addon can capture chat and show UI, but cannot call DeepL or any translation API. The companion app bridges this gap by reading the addon's memory buffer from outside the game.

This is the same approach used by **WeakAuras Companion** and **WarcraftLogs** — read-only memory access, fully compliant with Blizzard's Terms of Service.

## Installation

### Quick Start

1. Download `BabelChat.zip` from [Releases](https://github.com/Yumash/BabelChat/releases)
2. Extract and run `BabelChat.exe` **as Administrator**
3. Follow the setup wizard (get a [free DeepL API key](https://www.deepl.com/pro-api), set WoW path, install addon)
4. Launch WoW, join a group — translations appear automatically

### From Source

```bash
git clone https://github.com/Yumash/BabelChat.git
cd BabelChat
pip install -r requirements.txt
python -m app.main  # run as Administrator
```

### WoW Addon (Manual)

Copy `addon/BabelChat/` to `World of Warcraft/_retail_/Interface/AddOns/BabelChat/`

## WoW Glossary

BabelChat includes a dictionary of **314 gaming terms** in **14 languages**, organized by category:

| Category | Examples | Count |
|----------|----------|-------|
| Social | ty, thx, np, gj, lol, gg, brb, omw | 71 |
| Classes & Specs | warrior, dk, ret, bm, disc, resto | 59 |
| Raid & Dungeon | trash, wipe, nerf, ninja, boe, cd | 54 |
| Combat | aggro, aoe, cc, dps, heal, tank, dot | 33 |
| Groups | lfm, lf1m, lf2m, premade | 29 |
| Stats | hp, mana, crit, haste, mastery | 19 |
| Professions | jc, bs, enchant, herb, alch, tailor | 17 |
| Status | afk, oom, brb, omw | 11 |
| Trade | wtb, wts, wtt, cod, mats, bis | 8 |
| Roles | tank, healer, dps | 7 |
| Guild | gm, officer, recruit, gbank | 5 |

Dictionary terms are shown as clean annotations below the original message — the chat stays readable.

### Contributing terms

Adding a new term is simple. Edit the relevant `addon/BabelChat/Data/*.lua` file:

```lua
["newterm"] = {
    enUS = "English translation",
    esES = "Traducción española",
    ruRU = "Русский перевод",
    deDE = "Deutsche Übersetzung",
    frFR = "Traduction française",
    -- ... (14 languages total)
},
```

## Blizzard ToS Compliance

| Aspect | Status |
|--------|--------|
| Memory reading | Read-only. Same as WeakAuras Companion, WarcraftLogs |
| Overlay | Allowed. Same as Discord Overlay |
| Addon API | Standard CHAT_MSG_* hooks. Used by every chat addon |
| No injection | No DLL injection, no hooking, no writing to WoW memory |
| No automation | No automated actions. Outgoing translation via manual clipboard paste |

## Limitations

- **Windows only** — ReadProcessMemory is a Windows API
- **Requires Administrator** — memory reading needs elevated privileges
- **DeepL Free limit** — 500K chars/month (~10K messages). Paid plans available
- **Outgoing messages** — copy → paste in WoW chat (by design, ToS compliance)

## Tech Stack

| Component | Technology |
|-----------|-----------|
| App | Python 3.12, PyQt6 |
| Memory Reader | pymem (ReadProcessMemory) |
| Language Detection | lingua-py (offline) |
| Translation | DeepL API |
| Cache | SQLite + LRU |
| Build | PyInstaller → single .exe |
| Addon | Lua 5.1, WoW API |
| Tests | 133 tests (pytest) |

## Development

```bash
python -m app.main    # Run
pytest                # Test (133 tests)
ruff check app/       # Lint
pyinstaller build.spec  # Build .exe
```

## Support the Project

This project is a collaboration between two authors:

| Component | Author | Support |
|-----------|--------|---------|
| **WoW Glossary** — 314 terms in 14 languages, in-game dictionary idea | **Pirson** | [Buy Me a Coffee](https://buymeacoffee.com/franciscorb) |
| **Companion App** — overlay, DeepL translation, memory reader, streaming | **Andrey Yumashev** | [Donate](https://yumatech.ru/donate/) |

## Documentation

- **[User Guide](docs/user/README.md)** — quick start, configuration, FAQ
- **[Technical Docs](docs/tech/README.md)** — architecture, memory reader, pipeline, addon internals

## Acknowledgements

- **[WoW Translator](https://www.curseforge.com/wow/addons/wow-translator)** by **Pirson** (MIT License) — WoW term glossary in 14 languages. BabelChat's dictionary is based on this addon's data.

## Authors

- **Andrey Yumashev** — [@Yumash](https://github.com/Yumash) — companion app, overlay, memory reader
- **Pirson** — [CurseForge](https://www.curseforge.com/wow/addons/wow-translator) — WoW dictionary engine and data
- **Claude** (Anthropic) — AI co-author

## License

[MIT License](LICENSE)
