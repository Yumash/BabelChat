# FAQ & Troubleshooting

## General

### Why does BabelChat need Administrator privileges?
To read WoW's process memory via `ReadProcessMemory`. This is a Windows API that requires elevated privileges. Same requirement as WarcraftLogs and WeakAuras Companion.

### Is this safe? Will I get banned?
BabelChat only **reads** memory — it never writes, injects, or automates anything. This is the same approach used by WeakAuras Companion and WarcraftLogs. Warden (WoW's anti-cheat) does not flag read-only memory access.

### Why does translation take 0.5-2 seconds?
The original message appears **instantly**. The translation delay is the round-trip to DeepL's servers (your text → DeepL neural network → translation back). Common phrases (gg, ty, brb, hello) translate instantly from the built-in phrasebook — no API call needed.

### How many messages can I translate for free?
DeepL Free gives 500,000 characters/month — approximately 10,000 chat messages. For most players this is more than enough. DeepL paid plans offer unlimited translation.

## Overlay Issues

### The overlay is empty / no messages appear
1. Check that BabelChat addon is enabled in WoW (character select → AddOns)
2. Type `/babel` in WoW chat — you should see a help message
3. Check that the companion app shows "WoW: Connected" in the overlay title bar
4. Verify you're running BabelChat.exe **as Administrator**

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
Messages like "ok", "lol", "kk" are in the skip list — they're universal and don't need translation. Abbreviations like "gg", "ty" are translated via the phrasebook instead of DeepL.

### Translation quality is bad for gaming terms
The built-in glossary handles common terms (dps, lfm, wts). If DeepL mistranslates a gaming-specific phrase, it's because the neural network doesn't know WoW context. BabelChat sends a context hint to DeepL, but complex jargon may still be imperfect.

## Connection Issues

### "WoW: Searching..." in the overlay
The memory reader is scanning WoW's memory for the addon buffer. This can take 1-3 seconds on first connection, or after a `/reload`. If it persists:
1. Make sure BabelChat addon is installed and enabled
2. Try `/babel companion` in WoW chat to verify the buffer is active
3. Restart BabelChat.exe

### BabelChat can't find WoW
Make sure WoW is running before BabelChat tries to connect. The app will keep trying every 5 seconds.

## Addon Issues

### "/babel" doesn't work in WoW
1. Check that the addon is enabled: Character select → AddOns → BabelChat
2. Type `/reload` to reload addons
3. Check for Lua errors: `/console scriptErrors 1`

### I upgraded from ChatTranslatorHelper
BabelChat automatically migrates your settings from the old addon. Just install BabelChat and remove the old ChatTranslatorHelper folder from AddOns.
