# BabelChat

Chat in a language you don't read, translated where you're already looking.

## On its own

Install it and play. Nothing to configure, no account, no key.

Gaming terms get their meaning appended in grey on the same line:

```
wtb gilded crest, cod    wtb = Куплю · gilded = Золочёная эмблема · crest = Эмблема +1
```

**436 terms in 14 languages**, plus every zone and item-set name from LibBabble.
The language comes from your WoW client, so a Russian client glosses in Russian.

## With the companion app

For whole sentences rather than terms, run the free companion app from
<https://github.com/Yumash/BabelChat>. It reads this addon's chat buffer out of
the game's memory and shows translations in an overlay above WoW — reading
only, no injection, no automation. That describes it; it is not a permission
from Blizzard. The README there says what it does to the game and what we can't
promise — read it first. The addon on its own needs none of it.

While the app is running the addon stays quiet, so the same message is not
answered twice in different words. Turn on "show the gloss even when the app is
running" in `/babel config` if you want both.

## Commands

| Command | What it does |
|---|---|
| `/babel` | help |
| `/babel config` | settings panel |
| `/babel on` / `off` | glossary on or off |
| `/babel test` | try it on a sample message |
| `/babel companion` | companion buffer status |

## Credits

The glossary began as [WoW Translator](https://www.curseforge.com/wow/addons/wow-translator)
by **Pirson** (MIT), which contributed 314 terms across 14 languages. BabelChat
added slang and a current Endgame/Midnight set, rewrote the matching engine, and
built the companion app.

- **Pirson** — glossary data and the in-game translation idea — [Buy Me a Coffee](https://buymeacoffee.com/franciscorb)
- **Andrey Yumashev** — addon, companion app, translation engine
- **AhegaoZKun** — Linux/Wayland support, Microsoft Translator backend

MIT License. Full description, provider comparison and privacy notes:
<https://github.com/Yumash/BabelChat>
