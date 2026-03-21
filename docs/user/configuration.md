# Configuration

## Settings Dialog

Access via overlay toolbar button or system tray → Settings.

### General Tab

| Setting | Description |
|---------|-------------|
| DeepL API Key | Your API key with validation and usage quota display |
| WoW Path | Auto-detected or manual. "Install Addon" button copies addon to WoW |
| Interface Language | RU, EN, ES |
| Your Language | Messages in this language are not translated |
| Target Language | Foreign messages are translated to this language |
| Channels | Toggle: Party, Raid, Guild, Say/Yell, Whisper, Instance |
| Skip own messages | Don't translate your own messages (auto-detected player name) |

### Overlay Tab

| Setting | Description |
|---------|-------------|
| Opacity | 20-100% background transparency |
| Font size | 8-20pt |
| Translation ON by default | Start with translation enabled |
| Debug console | Show debug window (for troubleshooting) |

### Hotkeys Tab

| Default | Action |
|---------|--------|
| `Ctrl+Shift+T` | Toggle translation ON/OFF |
| `Ctrl+Shift+C` | Translate clipboard content |

Click any hotkey field and press your desired key combination to customize.

## WoW Addon Settings

In WoW: ESC → Interface → AddOns → BabelChat

| Section | Options |
|---------|---------|
| General | Enable/disable dictionary, translation color |
| Categories | 12 toggles for term categories |
| Channels | Which chat channels to translate |
| Language | Target language (14 available) |
| Companion | Enable/disable companion app buffer |
| Mode | Dictionary only / Overlay only / Both |

## Addon Commands

| Command | Description |
|---------|-------------|
| `/babel` | Show help |
| `/babel config` | Open WoW settings panel |
| `/babel on` / `off` | Toggle dictionary translation |
| `/babel test` | Test with sample message |
| `/babel companion` | Show companion buffer status |
| `/babel poll on` / `off` | Toggle GetMessageInfo fallback |
| `/babel log on` / `off` | Toggle chat file logging |

## config.json

All companion app settings are stored in `config.json` (auto-created). You can edit it manually if needed:

```json
{
  "deepl_api_key": "your-key:fx",
  "wow_path": "D:/World of Warcraft",
  "own_language": "RU",
  "target_language": "EN",
  "overlay_opacity": 180,
  "overlay_font_size": 10,
  "hotkey_toggle_translate": "Ctrl+Shift+T",
  "channels_party": true,
  "channels_raid": true,
  "channels_guild": true,
  "channels_say": true,
  "channels_whisper": true,
  "channels_instance": true,
  "skip_own_messages": true,
  "show_debug_console": false
}
```

A backup (`config.json.bak`) is created automatically before every save.
