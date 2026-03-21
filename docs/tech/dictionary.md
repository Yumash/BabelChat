# Contributing Dictionary Terms

## Format

Each term is a Lua table entry in `addon/BabelChat/Data/*.lua`:

```lua
["term"] = {
    enUS = "English",
    esES = "Español (España)",
    esMX = "Español (México)",
    deDE = "Deutsch",
    frFR = "Français",
    itIT = "Italiano",
    koKR = "한국어",
    ptBR = "Português",
    ruRU = "Русский",
    zhCN = "简体中文",
    zhTW = "繁體中文",
    plPL = "Polski",
    svSE = "Svenska",
    noNO = "Norsk"
},
```

## Categories

Pick the file that matches your term:

| File | Category | Examples |
|------|----------|----------|
| `Social.lua` | Chat phrases, emotes, reactions | ty, gg, lol, wp |
| `Slang.lua` | Gaming slang, chat shortcuts, M+ callouts | ez, copium, bricked, w2w, soak |
| `Clases.lua` | Class names, specializations | warrior, dk, ret, bm |
| `Combate.lua` | Combat mechanics | aggro, aoe, cc, dot |
| `Grupos.lua` | Group/party related | lfm, lf1m, premade |
| `Mazz_Raid.lua` | Raid/dungeon mechanics | trash, ninja, boe, debuff |
| `Profesiones.lua` | Profession abbreviations | jc, bs, enchant, herb |
| `Estadisticas.lua` | Character stats | crit, haste, mastery, vers |
| `Estado.lua` | Player status | afk, oom |
| `Comercio.lua` | Trade terms | wtb, wts, cod, mats |
| `Hermandad.lua` | Guild terms | gm, officer, recruit |
| `Roles.lua` | Role names | tank, healer, dps |

## Steps

1. Choose the correct category file
2. Copy an existing entry as template
3. Fill in all 14 languages (use the same value for esES/esMX if identical)
4. Key (the abbreviation) should be **lowercase**
5. Submit a pull request

## Rules

- **Lowercase keys** — DictEngine converts input to lowercase before matching
- **No duplicates** — check all files before adding (a term should exist in exactly one file)
- **Multi-word phrases** are supported — use space in the key: `"go next"`
- **Short keys (1-2 chars)** may cause false positives — avoid unless very specific
- Translations should be **natural** in each language, not literal
- When in doubt about a language, use the English value as fallback (`enUS`)

## Testing

After adding terms, test in WoW:
```
/babel test
```

Or type a message containing your term in chat and verify the annotation appears correctly.

## How DictEngine Uses Data

1. On addon load, `RebuildMasterDict()` iterates all enabled category files
2. Single-word terms → `MasterDict[lowercase_key] = translation`
3. Multi-word terms → `MultiWordPatterns[key]`, sorted by length (longest first)
4. On chat message, engine matches against both tables, skipping hyperlinks
5. Result: clean annotation below original message
