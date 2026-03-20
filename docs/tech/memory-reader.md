# Memory Reader

## Why Memory Reading?

WoW writes chat to `WoWChatLog.txt`, but uses an internal ~4KB buffer. The file updates only when the buffer fills — **real delay is 1-5 minutes**. Unacceptable for a chat translator.

Instead, we read the addon's Lua SavedVariable directly from WoW's process memory via `ReadProcessMemory`. Latency: **<1 second**.

## How It Works

The addon stores messages in `BabelChatDB.wctbuf` — a Lua string with markers:

```
__WCT_BUF_0042__
0|META|PLAYER|Thrall-Sargeras
1|RAW|SAY|Thrall-Sargeras|Hello everyone
2|DICT|GUILD|Jaina-Server|some text\ttranslated text
__WCT_END__
```

The companion app scans WoW's memory for these markers, then reads the content between them.

## Tiered Scan Cascade

Lua strings are immutable — every buffer flush creates a NEW string at a NEW address. The old one lingers until GC. We use a tiered strategy:

| Tier | Speed | Strategy |
|------|-------|----------|
| 0. Cached region | ~50ms | Re-scan the same memory region |
| 1. History | ~30ms | Scan regions where markers were previously found |
| 1.5. Neighborhood | ~200ms | ±16MB around last known address |
| 2. Heap scan | ~2-3s | All regions ≤8MB (parallel, 8 threads) |
| 3. Full scan | ~7-10s | Last resort — entire process memory |

## Zombie Buffer Detection

After GC, old Lua strings with valid markers remain in memory ("zombies"). The reader detects them via:

1. **Seq freshness** — tracks last 3 seq values. If unchanged for 3 polls and no new messages for 3s, triggers rescan
2. **Blacklist with TTL** — zombie addresses blacklisted for 60s, then expire (GC may reuse memory)
3. **Seq reset detection** — after `/reload`, addon restarts seq from 1. Reader detects the jump and resets tracking

## Buffer Format (v2.1)

```
SEQ|KIND|EVENT|author|text          (RAW — needs DeepL)
SEQ|DICT|EVENT|author|original\ttranslated  (DICT — addon dictionary translated, tab separator)
SEQ|META|key|value                  (META — metadata like player name)
```

- SEQ: monotonic counter (survives `/reload` via SavedVariable)
- KIND: RAW, DICT, or META
- EVENT: SAY, GUILD, RAID, WHISPER, etc.
- Tab separator between original and translated in DICT (pipes appear in WoW color codes)

## ToS Compliance

`ReadProcessMemory` is read-only. Warden (WoW anti-cheat) does not flag external read-only access. Same approach used by WeakAuras Companion and WarcraftLogs.
