# Quick Start

## Requirements

- Windows 10/11
- World of Warcraft (Retail — The War Within / Midnight)
- Free [DeepL API key](https://www.deepl.com/pro-api) (500K chars/month, takes 2 minutes to get)

## Step 1: Download

Download `BabelChat.zip` from [GitHub Releases](https://github.com/Yumash/BabelChat/releases).

Extract anywhere (Desktop, Downloads, wherever you like).

## Step 2: Run as Administrator

Right-click `BabelChat.exe` → **Run as administrator**.

> BabelChat needs admin privileges to read WoW's process memory. This is the same requirement as WarcraftLogs and WeakAuras Companion.

## Step 3: Setup Wizard

On first launch, a wizard walks you through 5 steps:

### 3.1 Welcome
Choose your interface language (English, Russian, or Spanish).

### 3.2 DeepL API Key
1. Click the link to open DeepL's registration page
2. Sign up for a **free** account (no credit card required for Free tier)
3. Go to your [DeepL Account](https://www.deepl.com/account/summary) → API Keys
4. Copy your key and paste it into BabelChat
5. Click "Validate" to verify it works

### 3.3 WoW Path
BabelChat tries to auto-detect your WoW installation. If it doesn't find it, click "Browse" and select your `World of Warcraft` folder.

### 3.4 Language
- **Your language** — the language you speak (messages in this language won't be translated)
- **Target language** — the language you want foreign messages translated TO

### 3.5 Install Addon
Click "Install Addon" to copy BabelChat into your WoW AddOns folder. Alternatively, copy `addon/BabelChat/` manually to:
```
World of Warcraft/_retail_/Interface/AddOns/BabelChat/
```

## Step 4: Launch WoW

1. Start World of Warcraft
2. On the character select screen, click **AddOns** and verify "BabelChat" is enabled
3. Log in to your character
4. You should see a welcome message in chat: *"Welcome to BabelChat!"*

## Step 5: Play

Join a group and chat. BabelChat will:
- Show the **original message immediately** in the overlay
- Show the **translation 0.5-2 seconds later** below it
- Common phrases (gg, ty, brb) translate **instantly** without any delay

## What You'll See

The overlay appears on top of WoW with a dark semi-transparent background:

- **Channel colors** match WoW's native chat colors (blue for Party, orange for Raid, green for Guild)
- **Original text** in gray
- **Translation** in gold, with an arrow: `→ translated text`
- **Filter tabs** at the top to show only specific channels

## Tips

- **Toggle translation** with `Ctrl+Shift+T` (customizable in Settings)
- **Reply in another language**: click the reply area, type your message, press Enter → translation is copied to clipboard → paste in WoW with `Ctrl+V`
- **Minimize overlay** by clicking the minimize button in the title bar
- **Move/resize** by dragging the title bar or bottom-right corner
- The overlay is **click-through** by default — clicks pass through to WoW
