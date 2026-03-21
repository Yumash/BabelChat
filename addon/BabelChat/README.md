# BabelChat

**Break the language barrier in World of Warcraft.**

BabelChat is a chat translation addon with an optional companion app. It works in two modes:

## Standalone Mode (Addon Only)

The addon translates **gaming slang, abbreviations, and WoW-specific terms** directly in your chat window using a built-in dictionary of **347 terms in 14 languages**.

When someone types `lfm icc hc need heal`, you see a clean annotation below:
> → looking for more, Icecrown Citadel, heroic, need healer

No external app needed. No API keys. Works out of the box.

**Supported languages:** English, Spanish, German, French, Italian, Portuguese, Russian, Korean, Chinese (Simplified & Traditional), Polish, Swedish, Norwegian.

## Companion Mode (Addon + Desktop App)

For **full sentence translation** via DeepL, download the free companion app from [GitHub](https://github.com/Yumash/BabelChat). The app reads the addon's memory buffer and shows translations in a sleek overlay on top of WoW — with less than 2 seconds latency.

The companion app is **read-only** (no injection, no automation) — same approach as WeakAuras Companion and WarcraftLogs.

## Dictionary Categories

| Category | Examples | Terms |
|----------|----------|-------|
| Social & Slang | ty, gg, brb, ez, copium, go next | 104 |
| Classes & Specs | dk, ret, bm, disc, resto, boomkin | 59 |
| Raid & Dungeon | wipe, prog, soak, kite, brez, vault | 54 |
| Combat | aggro, aoe, cc, dps, dot, cleave | 33 |
| Groups | lfm, lf1m, premade, pug | 29 |
| Stats | crit, haste, mastery, vers, ilvl | 19 |
| Professions | jc, bs, enchant, herb, alch, tailor | 17 |
| Status | afk, oom, dc, rdy | 11 |
| Trade | wtb, wts, bis, mats, cod | 8 |
| Roles | tank, healer, dps | 7 |
| Guild | gm, officer, recruit, gbank | 5 |
| Zones | 5000+ zone names via LibBabble | - |

## Slash Commands

| Command | Description |
|---------|------------|
| `/babel` | Show help |
| `/babel config` | Open settings panel |
| `/babel on` / `off` | Toggle dictionary translation |
| `/babel test` | Test translation with a sample message |
| `/babel companion` | Show companion app buffer status |

## Key Differences from WoW Translator

BabelChat is inspired by [WoW Translator](https://www.curseforge.com/wow/addons/wow-translator) by **Pirson** and includes his dictionary data (MIT License). Key differences:

| | WoW Translator | BabelChat |
|---|---|---|
| Dictionary terms | 314 | 347 (+slang category) |
| Full sentence translation | No | Yes (via DeepL companion app) |
| Translation display | Inline color codes in chat | Clean annotation below message |
| Hyperlink handling | Can break item links | Hyperlink-aware (skips links) |
| Overlap protection | No | Yes (prevents double translations) |
| Companion app | No | Free overlay with streaming translation |
| Slash command | /wt | /babel |

## Credits

- **Pirson** — Original WoW Translator addon, dictionary data (314 terms × 14 languages). [Buy Me a Coffee](https://buymeacoffee.com/franciscorb)
- **Andrey Yumashev** — BabelChat addon integration, companion app, DictEngine v2

## License

MIT License — free to use, modify, and distribute.
