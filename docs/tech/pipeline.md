# Translation Pipeline

## Overview

Every chat message goes through a multi-stage pipeline. The key innovation is **streaming** — the original message appears in the overlay immediately, and the translation is added when DeepL responds.

## Stages

```
Message from memory reader
    │
    ▼
1. Parse (regex, channel detection)
    │
    ▼
2. Dedup (author+text, 60s TTL, monotonic clock, thread-safe lock)
    │
    ▼
3. Channel filter (configurable per channel)
    │
    ▼
4. NPC filter (names with spaces in Say/Yell)
    │
    ▼
5. Own message filter (skip translation for your own messages)
    │
    ▼
6. Translation enabled check
    │
    ▼
7. Clean text (strip WoW color codes)
    │
    ▼
8. Abbreviation check — gg, ty, brb → instant from phrasebook
    │
    ▼
9. Language detection (lingua-py, offline, ~1ms)
    │                                          │
    ├── Own language detected → emit without   │
    │   translation                            │
    │                                          │
    ▼                                          │
10. Phrasebook lookup — "привет" → "hello"     │
    │                                          │
    ▼                                          │
11. Cache lookup (SQLite + in-memory LRU)      │
    │                                          │
    ▼                                          │
12. ━━ STREAMING SPLIT ━━━━━━━━━━━━━━━━━━━━━━━━┘
    │
    ├── Emit original message (msg_id=N, is_update=False)
    │   → user sees original text IMMEDIATELY
    │
    ▼
13. Strip URLs/markers → Expand slang → Expand WoW terms
    │
    ▼
14. DeepL API call (0.5-2s, with retry + exception fallback)
    │
    ▼
15. Restore tokens → Cache result
    │
    ▼
16. Emit translation update (msg_id=N, is_update=True)
    → overlay replaces last line with original + translation
```

## Thread Safety

`_on_new_line` is called from the memory reader thread. Critical shared state:

- `_recent_messages` — protected by `self._lock` (threading.Lock)
- `_config` — snapshot at method start (`cfg = self._config`)
- `_next_msg_id` — incremented under lock
- `_on_message` callback — emits Qt signal (thread-safe cross-thread delivery)

## Streaming Protocol

The overlay receives `TranslatedMessage` objects with two new fields:

```python
@dataclass
class TranslatedMessage:
    original: ChatMessage
    translation: TranslationResult | None
    source_lang: str = ""
    msg_id: int = 0        # unique ID for streaming
    is_update: bool = False  # True = replaces previous msg_id
```

- **Phase 1**: `msg_id=42, is_update=False, translation=None` → overlay shows original
- **Phase 2**: `msg_id=42, is_update=True, translation=result` → overlay replaces with original + translation

Instant hits (phrasebook, cache) skip streaming — emit once with translation included.

## Performance

| Path | Latency | API calls |
|------|---------|-----------|
| Abbreviation hit (gg, ty) | ~0ms | 0 |
| Phrasebook hit ("hello") | ~1ms | 0 |
| Cache hit | ~1ms | 0 |
| DeepL translation | 500-2000ms | 1 |
| Own language | ~1ms | 0 |
