# FAQ & Troubleshooting

## General

### Does BabelChat need Administrator privileges?
No. `ReadProcessMemory` against a process owned by the same user works without
them, and BabelChat used to ask for them anyway. It no longer does: standing
elevation turns an ordinary library-planting bug into a full compromise, so the
build dropped the request. If you have a shortcut set to "run as administrator"
from an older version, clear it.

### Is this safe? Will I get banned?
Nobody outside Blizzard can answer that, and we won't pretend to. The companion opens the game process for reading only and never writes, injects or automates — but Blizzard's EULA names *reading* the game's data as prohibited without authorization, and its Anti-Cheating Agreement says processes holding a handle to the game are inspected. We know of no account action over BabelChat; that is not the same as permission. The README section [What it does to the game, and what we can't promise](../../README.md#what-it-does-to-the-game-and-what-we-cant-promise) quotes the clauses. The addon on its own is an ordinary UI add-on and carries none of this — if the risk isn't for you, use it without the companion.

### Why not just read the chat log file?
We tried. WoW buffers `WoWChatLog.txt` with a ~4KB write buffer and flushes unpredictably — delays range from 1 to 5+ minutes, messages arrive in random-order bursts. For a real-time translator, that's useless. Our addon writes to a Lua string in memory, and the companion reads it every 250ms — sub-second latency. This approach is unique: WeakAuras Companion reads SavedVariables from disk (needs `/reload`), WarcraftLogs tails the combat log (not available for chat).

### Why does translation take 0.5-2 seconds?
The original message appears **instantly**. The delay is the round trip to
whichever provider you configured. Common phrases (gg, ty, brb, hello) and
glossary terms resolve instantly from data that ships with the app — no network
call at all.

### Which provider should I use?
Whichever you can actually sign up for. **GigaChat** is the default because it
is free for individuals, needs only a Sber ID rather than a card, and works from
Russia without a VPN. **MyMemory** needs no account whatsoever and is always
available as a fallback, so translation works before you configure anything.
DeepL gives the best quality but asks for a card to verify identity; Microsoft
Translator is free but needs an Azure account.

### How many messages can I translate for free?
Depends on the provider: GigaChat gives 1M tokens a year, DeepL 500,000
characters a month (roughly 10,000 messages), Microsoft 2M characters a month,
MyMemory 5,000 words a day — 50,000 if you enter an email. If one runs out, the
next configured provider is tried automatically.

### Can I use more than one provider at once?
Yes, and it is the point of the "Preferred" setting. The preferred one is tried
first; if it fails or hits its quota, the others are tried in turn rather than
the message being dropped.

## Overlay Issues

### The overlay is empty / no messages appear
1. Check that BabelChat addon is enabled in WoW (character select → AddOns)
2. Type `/babel` in WoW chat — you should see a help message
3. Check that the companion app shows "WoW: Connected" in the overlay title bar
4. If WoW itself is running as administrator, run BabelChat the same way —
   a normal-privilege process cannot read an elevated one. Neither needs
   elevation on its own.

### The overlay covers important parts of my screen
- **Drag** the title bar to move it
- **Resize** by dragging the bottom-right corner
- **Minimize** by clicking the minimize button
- The overlay remembers its position and size between sessions

### Clicks go through the overlay to WoW
This is by design — the overlay is click-through so you can play normally. To interact with the overlay, hover over the title bar area.

## Translation Issues

### Messages in my own language are being translated
Check Settings → General → "Your Language". Make sure it's set correctly. BabelChat auto-detects language, but the "your language" setting tells it which to skip.

### Some short messages aren't translated
Messages like "ok", "lol", "kk" are in the skip list — they're universal and don't need translation. Abbreviations like "gg", "ty" come from the phrasebook instead of going to a translation provider.

### Translation quality is bad for gaming terms
The built-in glossary handles common terms (dps, lfm, wts) without a network
call. When a provider mistranslates gaming jargon, it is because the model has
no WoW context; BabelChat sends a context hint with each request, but complex
jargon may still come back imperfect.

The addon also glosses terms directly in the chat frame — `wts bis ring 500k`
gets `wts = продаю · bis = лучшее в слоте` appended in grey on the same line.
That works with no companion app and no key at all. It stays quiet while the
companion is running, so the same message isn't answered twice in different
words — tick "always show the gloss" in `/babel config` if you want both.

## Connection Issues

### "WoW: Searching..." in the overlay
The reader is looking for the anchor the addon parks in memory for it. That takes a second or two on the first connection and after a `/reload`; from then on it follows a pointer and finds the buffer without searching. If it persists:
1. Make sure BabelChat addon is installed and enabled
2. Try `/babel companion` in WoW chat to verify the buffer is active
3. Restart BabelChat.exe

### Chat stops being translated inside a Mythic+ key

This is the game, not the addon. From Midnight on, while a keystone is running
Blizzard hands chat text to addons as a *secret value*: it looks like a string
and raises an error the moment anything reads it. No addon can read chat during a
key — BabelChat included, and every other chat addon too.

The overlay says so rather than looking broken, and translation comes back by
itself when the key ends. Raids, dungeons without a key, and everything outside a
run are unaffected. The same applies inside a rated PvP match.

### BabelChat can't find WoW
Make sure WoW is running before BabelChat tries to connect. The app will keep trying every 5 seconds.

## Addon Issues

### "/babel" doesn't work in WoW
1. Check that the addon is enabled: Character select → AddOns → BabelChat
2. Type `/reload` to reload addons
3. Check for Lua errors: `/console scriptErrors 1`

### I upgraded from ChatTranslatorHelper
BabelChat automatically migrates your settings from the old addon. Just install BabelChat and remove the old ChatTranslatorHelper folder from AddOns.
