![BabelChat](https://github.com/Yumash/BabelChat/raw/main/assets/icon.png)

# BabelChat

**Break the language barrier in World of Warcraft**  
Real-time chat translation with a smart overlay — companion app + WoW addon

[Русская версия](https://github.com/Yumash/BabelChat/blob/main/README_ru.md) | [Versión en español](https://github.com/Yumash/BabelChat/blob/main/README_es.md)

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/Yumash/BabelChat/blob/main/LICENSE) [![Python](https://img.shields.io/badge/Python-3.12+-yellow.svg)](https://python.org) [![Release](https://img.shields.io/github/v/release/Yumash/BabelChat?include_prereleases)](https://github.com/Yumash/BabelChat/releases) [![CurseForge](https://img.shields.io/curseforge/dt/1491616?logo=curseforge&logoColor=white&label=CurseForge&color=F16436)](https://www.curseforge.com/wow/addons/babelchat) [![Wago](https://img.shields.io/badge/Wago-Addons-C1272D?logo=wago&logoColor=white)](https://addons.wago.io/addons/96d2BEGO)

---

![BabelChat Demo](https://github.com/Yumash/BabelChat/raw/main/assets/demo.webp)

*The overlay opens, collapses, gets dragged around, and English turns into Russian — while the addon glosses the same line in chat underneath. [Full quality](https://github.com/Yumash/BabelChat/raw/main/assets/demo.mp4).*

## The Problem

You join a PUG raid. The tank explains tactics — in Spanish. The healer asks something — in German. You speak English (or Russian, or French). Nobody understands each other. The pull happens, people die, and someone types "gg noob" — the only phrase everyone knows.

**This happens constantly** in WoW's cross-realm and cross-region groups. Language barriers ruin coordination, cause wipes, and make the game less fun.

## The Solution

BabelChat translates WoW chat **in real time**. A tiny addon captures messages directly from the game; a companion app sends them to a translation provider and shows the result in a sleek overlay on top of WoW.

**You see the original message instantly. The translation appears 0.5–2 seconds later.**

Common phrases like "gg", "ty", "ready?", "pull" translate instantly from a built-in phrasebook — no API call, no delay. Full sentences go to the provider and arrive within 1–2 seconds. The same message is never translated twice (cached).

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
- **Built-in phrasebook** — 53 phrases + 75 gaming abbreviations translated instantly without API
- **WoW glossary** — 436 gaming terms (lfm, wts, dps, tank, etc.) in 14 languages
- **Channel filters** — Party, Raid, Guild, Say, Yell, Whisper, Instance, Trade, General, Services, LFG, player-made channels, Emote
- **Four translation providers** — GigaChat (the default), MyMemory, DeepL, Microsoft. If the preferred one fails or runs out of quota, the next configured one takes the message
- **Translation cache** — thread-safe SQLite + LRU, same text never translated twice
- **Global hotkeys** — toggle translation without leaving the game
- **Cross-platform** — Windows and Linux (via Proton/Wine) supported

## Translation Providers

Four providers ship with the app. The chain is tried in this order, and a
provider that fails or runs out of quota hands the message to the next one:

| Provider | What it costs | What it needs |
| --- | --- | --- |
| **GigaChat** (Sber) — the default | Free for individuals: 1M tokens a year, roughly 50,000–70,000 messages | A Sber ID. No card. Works from Russia without a VPN — [how to get a key](https://github.com/Yumash/BabelChat/blob/main/docs/user/gigachat.md) |
| **MyMemory** | Free | Nothing at all. It works on first launch before you configure anything, which is why translation is never dead on arrival. Quality is below the others, so it sits under them in the chain |
| **DeepL** | Free tier: 500K characters a month (~10K messages) | Sign-up asks for a card to verify identity; it is never charged |
| **Microsoft Translator** | Free tier: 2M characters a month, no card | An Azure account |

GigaChat leads because it is the only one of the four a player in Russia can
sign up for without a foreign card or a VPN. Any of them can be made the
preferred provider in *Settings → General*, and the setup wizard asks on first
run.

## Why Does Translation Take 0.5–2 Seconds?

BabelChat uses **progressive rendering** (streaming):

1. **You see the original message immediately** (0ms delay)
2. **The translation is appended to the same line**, after an arrow, when the provider responds (0.5–2s)

The delay is the provider round-trip — your text travels to their servers, gets translated by a neural network, and comes back. This is the same latency as Google Translate or any cloud translation service.

**What's instant (no delay):**
- Gaming abbreviations: `gg`, `ty`, `brb`, `afk`, `wp`, `lol` — translated from built-in phrasebook
- Common phrases: "hello", "thanks", "ready?", "good game" — phrasebook
- Repeated messages — served from cache
- Messages in your own language — shown without translation

**What takes 0.5–2s:**
- Full sentences in foreign languages — a provider API call is required
- First occurrence of any phrase — subsequent ones are cached

## How It Works

```
┌──────────────────────────────────────────────────────────┐
│  World of Warcraft                                       │
│                                                          │
│  BabelChat addon                                         │
│  ├── Hooks CHAT_MSG_* events via standard WoW API        │
│  ├── Ring buffer (50 messages, flushed every 250ms)      │
│  └── Writes to BabelChatDB.wctbuf (Lua SavedVariable)    │
└──────────┬───────────────────────────────────────────────┘
           │  Memory read (every 250ms), through a pointer the addon
           │  parks for it — no searching, ~0.1% of one core
           │  Windows: ReadProcessMemory / Linux: process_vm_readv
           ▼
┌──────────────────────────────────────────────────────────┐
│  Companion App (Python + Rust)                           │
│                                                          │
│  Rust Scanner ──→ Parser ──→ Language Detector           │
│       │                           │                      │
│       │    Phrasebook (instant) ──┤                      │
│       │    Cache (instant)  ──────┤                      │
│       │    Provider API (0.5-2s) ─┤                      │
│       │                           ▼                      │
│       └──────────→ Smart Overlay (PyQt6 / GTK4)          │
└──────────────────────────────────────────────────────────┘
```

### Why a companion app (not just an addon)?

WoW's Lua sandbox **cannot make HTTP requests**. The addon can capture chat and show UI, but cannot call a translation API. The companion app bridges this gap by reading the addon's memory buffer from outside the game.

BabelChat only **reads** memory — it never writes, injects, or automates anything. Warden (WoW's anti-cheat) does not flag read-only access.

> **Why not just read WoWChatLog.txt?** We tried. WoW buffers the chat log file with a ~4KB write buffer and flushes unpredictably — delays range from 1 to 5+ minutes. Messages arrive in random-order bursts, not in real time. For a translator, that's useless. Our addon writes to a Lua string in memory, and the companion reads it every 250ms — giving us sub-second latency.

## Upgrading from ChatTranslatorHelper

If you used our previous addon (ChatTranslatorHelper, TWW era), BabelChat automatically migrates your settings. Just install BabelChat and delete the old `ChatTranslatorHelper` folder from `Interface/AddOns/`.

## Installation

### Windows — Quick Start

1. Download `BabelChat.zip` from [Releases](https://github.com/Yumash/BabelChat/releases)
2. Extract and run `BabelChat.exe`
3. Follow the setup wizard (pick a translator, set the WoW path, install the addon). GigaChat is free for individuals and needs no card; you can also skip this and use the in-game dictionary alone.
4. Launch WoW, join a group — translations appear automatically

### Linux  — Quick Start

1. Download the `.AppImage`, `.deb` or `.rpm` from [Releases](https://github.com/Yumash/BabelChat/releases) — the AppImage needs no installation, the packages install as `babelchat`
2. Run it (`chmod +x BabelChat-*.AppImage && ./BabelChat-*.AppImage`, or `babelchat` once the package is installed)
3. Follow the setup wizard (pick a translator, set the WoW path, install the addon). GigaChat is free for individuals and needs no card; you can also skip this and use the in-game dictionary alone.
4. Launch WoW, join a group — translations appear automatically

The addon on its own is `BabelChat-Addon.zip` in the same release — unzip it into
`Interface/AddOns/` if you only want the in-game dictionary.

### From Source (Windows)

```bash
git clone https://github.com/Yumash/BabelChat.git
cd BabelChat
pip install -r requirements.txt
python -m app.main
```

### From Source (Linux)

```bash
git clone https://github.com/Yumash/BabelChat.git
cd BabelChat
echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope

# Build the Rust scanner (required for Linux)
cargo build --release --manifest-path babelchat_scanner_linux/Cargo.toml
cp babelchat_scanner_linux/target/release/libbabelchat_scanner.so app/

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main_gtk
```

The addon does not write its memory buffer until you switch the companion on:
in WoW, `/babel config` → **Companion app** → tick the checkbox. Without it the
in-game dictionary works and the overlay stays empty.

### WoW Addon (Manual)

Copy `addon/BabelChat/` to `World of Warcraft/_retail_/Interface/AddOns/BabelChat/`

## WoW Glossary

BabelChat includes a dictionary of **436 gaming terms** in **14 languages**, organized by category:

| Category        | Examples                             | Count |
| --------------- | ------------------------------------ | ----- |
| Social          | ty, thx, np, gj, lol, gg, brb, omw   | 83    |
| Raid & Dungeon  | trash, wipe, nerf, ninja, boe, cd    | 63    |
| Classes & Specs | warrior, dk, ret, bm, disc, resto    | 59    |
| Slang           | glhf, copium, pug, brez, kite, diff  | 49    |
| Combat          | aggro, aoe, cc, dps, heal, tank, dot | 39    |
| Groups          | lfm, lf1m, lf2m, premade             | 36    |
| Endgame         | delve, keystone, affix, warband, ksm | 26    |
| Stats           | hp, mana, crit, haste, mastery       | 25    |
| Professions     | jc, bs, enchant, herb, alch, tailor  | 17    |
| Status          | afk, oom, brb, omw                   | 14    |
| Roles           | tank, healer, dps                    | 11    |
| Trade           | wtb, wts, wtt, cod, mats, bis        | 9     |
| Guild           | gm, officer, recruit, gbank          | 5     |

Two more categories have no data file of their own: zone names and item-set
names come from LibBabble, and each has its own toggle in the addon's options.

Glossed terms are appended to the message itself, in grey, as `term = meaning`
pairs separated by a middle dot — at most three, then a count. Keeping it on
one line is what makes a busy Trade channel readable, and it leaves copy-chat
working. When the companion app is running, the addon stays quiet and lets the
overlay do the talking instead of both answering the same message.

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

| Aspect         | Status                                                                      |
| -------------- | --------------------------------------------------------------------------- |
| Memory reading | Read-only. No writing, no injection. Warden does not flag read-only access  |
| Overlay        | Allowed. Same as Discord Overlay                                            |
| Addon API      | Standard CHAT\_MSG\_\* hooks. Used by every chat addon                      |
| No injection   | No DLL injection, no hooking, no writing to WoW memory                      |
| No automation  | No automated actions. Outgoing translation via manual clipboard paste       |

## Privacy — what leaves your machine

BabelChat translates by sending message text to a translation provider. That
means **other players' messages go to a third party**, including whispers and
guild chat, and those players never agreed to it. Worth knowing before you
switch channels on:

- **What is sent:** the text of messages in the channels you enabled, and
  nothing else. Channels you untick are dropped before any request is made.
- **Who receives it:** whichever provider you configured — GigaChat (Sber),
  MyMemory, DeepL or Microsoft. Each has its own privacy policy.
- **What is stored locally:** translations are cached for seven days, source
  text included, so the same line is not paid for twice. *Settings → Clear
  translation cache* deletes all of it.
- **What is not stored:** nothing is written to disk about captured chat unless
  you switch on *Write captured chat to a file* for troubleshooting. That file
  holds every message in full — turn it off when you are done.
- **Whispers** are the most sensitive channel and are on by default. If you
  share a machine, or translate in a guild that would not expect it, untick it.

The in-game dictionary alone sends nothing anywhere: it runs entirely inside
WoW, so an addon-only setup has no egress at all.

## Limitations

- **Reads the game's memory** — no elevation needed on Windows (the scanner asks only for read access to a process you already own); on Linux this needs `ptrace_scope=0`
- **Linux compositor** — the overlay sits above a fullscreen game only where layer-shell exists. On X11 it falls back to an always-on-top window; on GNOME Wayland neither is available and the app runs in a plain window, which it says on first start
- **Free-tier limits** — every provider has one (see the table above). When one runs out the chain moves to the next
- **Outgoing messages** — copy → paste in WoW chat (by design, ToS compliance)

## Tech Stack

| Component          | Technology                                                                 |
| ------------------ | -------------------------------------------------------------------------- |
| App                | Python 3.12, PyQt6 (Windows) / GTK4 + layer-shell (Linux)                  |
| Memory Reader      | Rust cdylib; reads through a pointer the addon parks, not by searching     |
| Rust Scanner       | Anchor + pulse; a full sweep only as a fallback; idle-priority threads     |
| Language Detection | lingua-py (offline)                                                        |
| Translation        | GigaChat, MyMemory, DeepL, Microsoft — tried in that order                 |
| Cache              | SQLite + LRU                                                               |
| Build              | PyInstaller → .exe (Windows) / AppImage, .deb, .rpm (Linux)                |
| Addon              | Lua 5.1, WoW API                                                           |
| Tests              | 1146 tests (pytest)                                                         |

## Development

```bash
python -m app.main        # Run (Windows)
python -m app.main_gtk    # Run (Linux)
pytest                    # Test
ruff check .              # Lint

# Linux: build Rust scanner before running
cargo build --release --manifest-path babelchat_scanner_linux/Cargo.toml
cp babelchat_scanner_linux/target/release/libbabelchat_scanner.so app/

# Build binaries
pyinstaller build.spec          # Windows .exe
pyinstaller build-linux.spec    # Linux binary
```

## Support the Project

This project is a collaboration between three authors:

| Component                                                                | Author              | Support                                                 |
| ------------------------------------------------------------------------ | ------------------- | ------------------------------------------------------- |
| **Glossary origins** — 314 of the 436 terms, and the idea of glossing chat in-game | **Pirson**          | [Buy Me a Coffee](https://buymeacoffee.com/franciscorb) |
| **Companion App** — overlay, translation providers, memory reader, streaming | **Andrey Yumashev** | [Donate](https://yumatech.ru/donate/)               |

## Documentation

- **[User Guide](https://github.com/Yumash/BabelChat/blob/main/docs/user/README.md)** — quick start, configuration, FAQ
- **[Technical Docs](https://github.com/Yumash/BabelChat/blob/main/docs/tech/README.md)** — architecture, memory reader, pipeline, addon internals

## Acknowledgements

- **[WoW Translator](https://www.curseforge.com/wow/addons/wow-translator)** by **Pirson** (MIT License) — WoW term glossary in 14 languages. BabelChat's dictionary is based on this addon's data.

## Authors

- **Andrey Yumashev** — [@Yumash](https://github.com/Yumash) — companion app, overlay, memory reader
- **Pirson** — [CurseForge](https://www.curseforge.com/wow/addons/wow-translator) — WoW dictionary engine and data
- **AhegaoZKun** — [@AhegaoZKun](https://github.com/AhegaoZKun) — Linux/Wayland support, Rust memory scanners, Microsoft Translator backend
- **Claude** (Anthropic) — AI co-author


## Support the work

BabelChat is free and stays free. If it saved you a pug, this is where
support goes — it pays for the translation allowances the free tiers do not
cover and for the time.

[**Support with a card — SBP, Visa, Mastercard**](https://pay.cloudtips.ru/p/ea5537e6)

| | |
| --- | --- |
| USDT TRC20 | `TGaUz963ZaCoHrfoDDgy1sCvSrK1wsZvcx` |
| BTC | `1BkYvFT8iBVG3GfTqkR2aBkABNkTrhYuja` |
| TON | `UQDFaHBN1pcQZ7_9-w1E_hS_JNfGf3d0flS_467w7LOQ7xbK` |

## License

[MIT License](https://github.com/Yumash/BabelChat/blob/main/LICENSE)
