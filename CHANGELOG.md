# Changelog / История изменений / Registro de cambios

## [3.1.1] — 2026-03-25

### Changed / Изменено / Cambiado
- **Code cleanup:** removed 235 lines of dead pointer-chasing code from memory reader
- Extracted `DeduplicationBuffer` into standalone class with safety cap (10k entries)
- Replaced 40+ magic numbers with named constants across pipeline, overlay, memory reader
- Unified 5 duplicate scan-accept blocks into `_accept_marker()` helper
- Named regex groups in parser (`m.group('text')` instead of `m.group(4)`)
- Fixed race condition: `itertools.count()` for thread-safe message IDs
- Narrowed exception handlers (`RuntimeError | OSError` instead of bare `Exception`)
- Removed dead `dict_text` parameter, duplicate regex, unused variables
- Made `RE_WOW_LINK` public (was private `_RE_WOW_LINK` imported cross-module with `noqa`)

— **Чистка кода:** удалено 235 строк мёртвого pointer-chasing кода из memory reader
— Дедупликация вынесена в отдельный класс с лимитом 10k записей
— 40+ магических чисел заменены именованными константами
— 5 дублей scan-accept объединены в `_accept_marker()`
— Именованные группы в regex парсера
— Потокобезопасные ID через `itertools.count()`
— Сужены обработчики исключений, удалены мёртвые параметры и дубли

— **Limpieza de código:** eliminadas 235 líneas de código muerto de pointer-chasing
— Deduplicación extraída en clase independiente con límite de 10k entradas
— 40+ números mágicos reemplazados con constantes nombradas
— 5 bloques duplicados scan-accept unificados en `_accept_marker()`
— Grupos regex nombrados en el parser
— IDs thread-safe via `itertools.count()`
— Manejadores de excepciones restringidos, parámetros y duplicados eliminados

## [3.0.1] — 2026-03-20

### Fixed / Исправлено / Corregido
- **CRITICAL:** Race condition in dedup — `_recent_messages` accessed from multiple threads without lock, now protected by `threading.Lock`
- **CRITICAL:** Overlay memory leak — `_messages` list and QTextEdit grew without bound over long sessions, now capped at 500/1500
- Config torn reads — pipeline thread could see mix of old and new config values, now uses snapshot
- Translator crash on network errors — only `DeepLException` was caught, added `except Exception` fallback
- SQLite cache never cleaned up — `cleanup()` called on pipeline start to remove expired entries
- Config load silently reset to defaults — now logs warning on corrupt/missing config
- Dedup timestamps used `time.time()` (affected by NTP) — switched to `time.monotonic()`
- Empty payload from addon buffer caused wasted work — now skipped early

— **КРИТИЧНО:** Гонка в дедупликации — `_recent_messages` без блокировки из нескольких потоков, добавлен `threading.Lock`
— **КРИТИЧНО:** Утечка памяти в оверлее — список сообщений и QTextEdit росли бесконечно, ограничены 500/1500
— Разрыв чтения конфига — pipeline мог видеть смесь старых и новых значений, теперь snapshot
— Краш переводчика при сетевых ошибках — ловился только `DeepLException`, добавлен общий обработчик
— Кэш SQLite никогда не чистился — `cleanup()` вызывается при старте
— Config молча сбрасывался при повреждении — теперь логирует предупреждение
— Dedup использовал `time.time()` (чувствителен к NTP) — заменён на `time.monotonic()`
— Пустой payload из буфера создавал лишнюю работу — пропускается

— **CRÍTICO:** Condición de carrera en dedup — `_recent_messages` sin bloqueo desde múltiples hilos, protegido con `threading.Lock`
— **CRÍTICO:** Fuga de memoria en overlay — lista de mensajes y QTextEdit crecían sin límite, limitados a 500/1500
— Lecturas rotas de config — pipeline podía ver mezcla de valores viejos y nuevos, ahora usa snapshot
— Crash del traductor por errores de red — solo se capturaba `DeepLException`, añadido fallback general
— Caché SQLite nunca se limpiaba — `cleanup()` se ejecuta al iniciar
— Config se reiniciaba silenciosamente — ahora registra advertencia
— Dedup usaba `time.time()` (afectado por NTP) — cambiado a `time.monotonic()`
— Payload vacío del buffer causaba trabajo innecesario — ahora se omite

### Added / Добавлено / Añadido
- Renamed project: ChatTranslatorHelper → **BabelChat** (new identity, no CurseForge conflict)
- Slang dictionary category — 33 new terms: ez, copium, bricked, pumping, carry, wipe, lust, pug, soak, kite, gank, glad...
- Slash command `/babel` (replaces `/wt`)
- CurseForge packaging: `.pkgmeta`, addon README, BBCode description, separate `BabelChat-Addon.zip` in releases
- DB migration from old ChatTranslatorHelper (automatic on first load)
- Technical documentation (`docs/tech/`) and user guide (`docs/user/`)

— Переименование: ChatTranslatorHelper → **BabelChat** (новая идентичность, нет конфликта на CurseForge)
— Категория сленга — 33 новых термина: ez, copium, bricked, pumping, carry, wipe, lust, pug, soak, kite, gank, glad...
— Слеш-команда `/babel` (вместо `/wt`)
— Пакетирование CurseForge: `.pkgmeta`, README аддона, BBCode описание, отдельный `BabelChat-Addon.zip`
— Миграция БД из ChatTranslatorHelper (автоматически при первом запуске)
— Техническая документация (`docs/tech/`) и руководство пользователя (`docs/user/`)

— Renombrado: ChatTranslatorHelper → **BabelChat** (nueva identidad, sin conflicto en CurseForge)
— Categoría de jerga — 33 nuevos términos: ez, copium, bricked, pumping, carry, wipe, lust, pug, soak, kite, gank, glad...
— Comando `/babel` (reemplaza `/wt`)
— Empaquetado CurseForge: `.pkgmeta`, README del addon, descripción BBCode, `BabelChat-Addon.zip` separado
— Migración de BD desde ChatTranslatorHelper (automática al primer inicio)
— Documentación técnica (`docs/tech/`) y guía de usuario (`docs/user/`)

## [3.0.0] — 2026-03-20

### Added / Добавлено / Añadido
- Streaming translation — original message appears in overlay instantly, translation arrives 0.5-2s later (progressive rendering)
- Thread-safe translation cache with explicit `threading.Lock` (was relying on GIL)
- Atomic config save — write to temp file + `os.replace()`, backup `.bak`, auto-recovery from corrupt JSON
- Seq freshness tracking — detects frozen (zombie) buffers via 3-poll seq history, auto-triggers rescan
- Blacklist TTL (60s) — zombie addresses expire and get re-scanned after GC reclaims memory
- DictEngine v2: clean annotation line `→ term1, term2` below original (no more inline color spam)
- Hyperlink-aware dictionary matching — skips `|H...|h` and `|cff...|r` blocks in WoW chat
- Overlap guard — prevents double-matching of dictionary terms
- 28 new tests (105 → 133): pipeline E2E (8), parser robustness (20)

— Стриминг перевода — оригинал появляется в оверлее мгновенно, перевод подгружается через 0.5-2с (progressive rendering)
— Потокобезопасный кэш переводов с `threading.Lock` (раньше держался на GIL)
— Атомарное сохранение конфига — запись в temp файл + `os.replace()`, бэкап `.bak`, авто-восстановление из повреждённого JSON
— Отслеживание свежести seq — обнаруживает замороженные (зомби) буферы через историю 3 опросов, автоматический пересканирование
— TTL чёрного списка (60с) — зомби-адреса истекают и пересканируются после освобождения GC
— DictEngine v2: чистая аннотация `→ term1, term2` под оригиналом (без inline-спама цветами)
— Hyperlink-aware словарный поиск — пропускает блоки `|H...|h` и `|cff...|r` в WoW чате
— Защита от пересечений — предотвращает двойной перевод словарных терминов
— 28 новых тестов (105 → 133): pipeline E2E (8), парсер robustness (20)

— Traducción streaming — el mensaje original aparece instantáneamente en el overlay, la traducción llega 0.5-2s después (renderizado progresivo)
— Caché de traducción thread-safe con `threading.Lock` (antes dependía del GIL)
— Guardado atómico de config — escritura en archivo temp + `os.replace()`, backup `.bak`, auto-recuperación de JSON corrupto
— Seguimiento de frescura seq — detecta buffers congelados (zombie) via historial de 3 sondeos, re-escaneo automático
— TTL de lista negra (60s) — direcciones zombie expiran y se re-escanean después de que el GC libere memoria
— DictEngine v2: línea de anotación limpia `→ term1, term2` debajo del original (sin spam de colores inline)
— Coincidencia de diccionario consciente de hyperlinks — omite bloques `|H...|h` y `|cff...|r` en el chat de WoW
— Protección contra solapamientos — previene doble traducción de términos del diccionario
— 28 nuevos tests (105 → 133): pipeline E2E (8), parser robustez (20)

### Changed / Изменено / Cambiado
- DICT buffer separator changed from `|` to `\t` — fixes parsing when WoW color codes contain pipes
- Pipeline: `translation_enabled` check moved before text processing (skip early)
- Parser `parse_addon_line` updated for v2.1 format (RAW/DICT kind field)

— Разделитель DICT-буфера изменён с `|` на `\t` — исправляет парсинг когда WoW color codes содержат pipes
— Pipeline: проверка `translation_enabled` перенесена до обработки текста (ранний выход)
— Парсер `parse_addon_line` обновлён для формата v2.1 (поле KIND: RAW/DICT)

— Separador de buffer DICT cambiado de `|` a `\t` — corrige el parsing cuando los códigos de color WoW contienen pipes
— Pipeline: verificación `translation_enabled` movida antes del procesamiento de texto (salida temprana)
— Parser `parse_addon_line` actualizado para formato v2.1 (campo KIND: RAW/DICT)

### Fixed / Исправлено / Corregido
- SQLite `check_same_thread=False` without locking — now protected by `threading.Lock`
- Config corruption on crash — atomic write prevents partial file writes
- DICT messages with WoW color codes breaking parser (pipe in `|cffXXXXXX...|r`)
- DictEngine matching inside WoW hyperlinks (`|Hitem:...|h[Name]|h|r`)
- DictEngine overlapping matches producing duplicate translations

— SQLite `check_same_thread=False` без блокировки — теперь защищён `threading.Lock`
— Порча конфига при крэше — атомарная запись предотвращает частичную запись файла
— DICT-сообщения с WoW color codes ломали парсер (pipe в `|cffXXXXXX...|r`)
— DictEngine находил совпадения внутри WoW гиперссылок (`|Hitem:...|h[Name]|h|r`)
— Пересекающиеся совпадения DictEngine создавали двойные переводы

— SQLite `check_same_thread=False` sin bloqueo — ahora protegido por `threading.Lock`
— Corrupción de config al crashear — escritura atómica previene escrituras parciales
— Mensajes DICT con códigos de color WoW rompían el parser (pipe en `|cffXXXXXX...|r`)
— DictEngine encontraba coincidencias dentro de hyperlinks WoW (`|Hitem:...|h[Name]|h|r`)
— Coincidencias solapadas de DictEngine creaban traducciones duplicadas

## [2.2.2] — 2026-03-19

### Added / Добавлено / Añadido
- Parallel heap scan: 8-thread parallel ReadProcessMemory via ThreadPoolExecutor — scans 4000+ memory regions concurrently
- "Don't translate own messages" option in Settings → Overlay with auto-detected player name from addon META
- Spanish UI translations (153 strings) — full overlay and settings localization
- "Why Python?" section in README (EN/RU/ES) explaining architecture choice
- NPC message filter in chat history (names with spaces in Say/Yell channels)
- WoW color code stripping (|cXXXXXXXX...|r) from addon dictionary translations

— Параллельное сканирование кучи: 8 потоков ReadProcessMemory через ThreadPoolExecutor — 4000+ регионов памяти одновременно
— Опция «Не переводить свои сообщения» в Настройки → Оверлей с автоопределением имени игрока из META аддона
— Испанский перевод интерфейса (153 строки) — полная локализация оверлея и настроек
— Раздел «Почему Python?» в README (EN/RU/ES)
— Фильтр NPC-сообщений в истории чата (имена с пробелами в каналах Say/Yell)
— Удаление цветовых кодов WoW (|cXXXXXXXX...|r) из словарных переводов аддона

— Escaneo paralelo del heap: 8 hilos ReadProcessMemory via ThreadPoolExecutor — 4000+ regiones de memoria simultáneamente
— Opción "No traducir mis mensajes" en Ajustes → Overlay con detección automática del nombre del jugador desde META del addon
— Traducciones de la interfaz al español (153 cadenas) — localización completa del overlay y ajustes
— Sección "¿Por qué Python?" en README (EN/RU/ES)
— Filtro de mensajes NPC en el historial de chat (nombres con espacios en canales Say/Yell)
— Eliminación de códigos de color WoW (|cXXXXXXXX...|r) de las traducciones del diccionario del addon

### Changed / Изменено / Cambiado
- DICT translation bypass — addon dictionary disabled for companion, all messages go through DeepL for consistent quality
- Dedup TTL increased from 30s to 60s — prevents duplicate messages from zombie Lua buffer copies
- Smart rescan threshold reduced from 3s to 1.5s — faster detection of buffer moves
- Rescan intervals reduced [2, 3, 5, 10]s (was [2, 5, 10, 30]s)
- Quick-to-full rescan threshold: 2 misses (was 5)

— Обход DICT-перевода — словарь аддона отключён для companion, все сообщения идут через DeepL для стабильного качества
— TTL дедупликации увеличен с 30с до 60с — предотвращает дубли от зомби-копий Lua-буфера
— Порог умного пересканирования снижен с 3с до 1.5с — быстрее обнаружение перемещения буфера
— Интервалы пересканирования уменьшены [2, 3, 5, 10]с (было [2, 5, 10, 30]с)
— Порог быстрого→полного пересканирования: 2 промаха (было 5)

— Bypass de traducción DICT — diccionario del addon desactivado para companion, todos los mensajes pasan por DeepL para calidad consistente
— TTL de dedup aumentado de 30s a 60s — previene mensajes duplicados de copias zombie del buffer Lua
— Umbral de re-escaneo inteligente reducido de 3s a 1.5s — detección más rápida de movimientos del buffer
— Intervalos de re-escaneo reducidos [2, 3, 5, 10]s (era [2, 5, 10, 30]s)
— Umbral de re-escaneo rápido→completo: 2 fallos (era 5)

### Fixed / Исправлено / Corregido
- Seq reset dedup bug — was saving texts from NEW buffer instead of delivered messages, causing all post-/reload messages to be skipped
- Player name property missing on MemoryChatWatcher wrapper class
- Lazy import crash for clean_message_text in pipeline

— Баг дедупликации при сбросе seq — сохранялись тексты из НОВОГО буфера вместо доставленных сообщений, из-за чего все сообщения после /reload пропускались
— Отсутствие свойства player name в классе-обёртке MemoryChatWatcher
— Краш ленивого импорта clean_message_text в pipeline

— Bug de dedup al reiniciar seq — se guardaban textos del buffer NUEVO en vez de mensajes entregados, causando que todos los mensajes post-/reload se omitieran
— Propiedad player name faltante en la clase wrapper MemoryChatWatcher
— Crash de importación lazy de clean_message_text en pipeline

### Performance / Производительность / Rendimiento
- ~50% messages delivered instantly via quick rescan (0-31ms)
- ~50% messages via heap scan (2.5-3.8s) — memory bandwidth limited at 3.3GB
- Pointer chasing prototype implemented (disabled) — needs WoW Lua internals research

— ~50% сообщений доставляются мгновенно через быстрое пересканирование (0-31мс)
— ~50% сообщений через сканирование кучи (2.5-3.8с) — ограничение пропускной способности памяти 3.3ГБ
— Прототип pointer chasing реализован (отключён) — требует исследования внутренностей WoW Lua

— ~50% mensajes entregados instantáneamente via re-escaneo rápido (0-31ms)
— ~50% mensajes via escaneo del heap (2.5-3.8s) — limitado por ancho de banda de memoria a 3.3GB
— Prototipo de pointer chasing implementado (desactivado) — necesita investigación de internos de WoW Lua

## [2.1.0] — 2026-03-18

### Added / Добавлено / Añadido
- Addon buffer format v2.1: SEQ|KIND|EVENT|author|text (DICT adds |translated)
- Dedup in BufferAddEntry (author+text TTL 2s) — fixes triple messages from multiple ChatFrames
- Addon buffers ALL channels regardless of dict.channels filter
- Pipeline: DICT messages show with dictionary translation (no DeepL call)
- Pipeline: RAW own-language messages shown without translation (conversation context)
- Single-instance guard via PID lock file (wct.lock) with TerminateProcess
- Zombie marker blacklist in memory reader
- Spanish localization in Locales.lua (full esES/esMX)

— Формат буфера аддона v2.1: SEQ|KIND|EVENT|author|text (DICT добавляет |translated)
— Дедупликация в BufferAddEntry (author+text TTL 2с) — исправляет тройные сообщения от нескольких ChatFrame
— Аддон буферизует ВСЕ каналы независимо от фильтра dict.channels
— Pipeline: DICT-сообщения отображаются со словарным переводом (без вызова DeepL)
— Pipeline: RAW-сообщения на своём языке отображаются без перевода (контекст беседы)
— Защита от повторного запуска через PID lock file (wct.lock) с TerminateProcess
— Чёрный список зомби-маркеров в memory reader
— Испанская локализация в Locales.lua (полная esES/esMX)

— Formato de buffer del addon v2.1: SEQ|KIND|EVENT|author|text (DICT añade |translated)
— Dedup en BufferAddEntry (author+text TTL 2s) — corrige mensajes triples de múltiples ChatFrames
— El addon almacena TODOS los canales independientemente del filtro dict.channels
— Pipeline: mensajes DICT se muestran con traducción del diccionario (sin llamada a DeepL)
— Pipeline: mensajes RAW en tu idioma se muestran sin traducción (contexto de conversación)
— Protección de instancia única via PID lock file (wct.lock) con TerminateProcess
— Lista negra de marcadores zombie en memory reader
— Localización al español en Locales.lua (completa esES/esMX)

### Changed / Изменено / Cambiado
- Version bumped to 2.1.0 across TOC, Core.lua, Config.lua, about_dialog.py

— Версия обновлена до 2.1.0 в TOC, Core.lua, Config.lua, about_dialog.py

— Versión actualizada a 2.1.0 en TOC, Core.lua, Config.lua, about_dialog.py

## [2.0.0] — 2026-03-16

### Added / Добавлено / Añadido
- Merged Pirson's WoW Translator dictionary engine — 313 WoW terms in 14 languages with inline chat translation
- LibBabble integration — 5000+ localized zone names, item sets, races, classes
- Addon settings panel in WoW (Interface > AddOns > Chat Translator) with category toggles, channel filters, language picker, color picker
- Minimap button for quick access to settings
- Companion app toggle — enable/disable memory buffer for overlay independently
- DICT/RAW message tagging — companion skips DeepL API for dictionary-matched messages
- Neighborhood scan — memory reader recovers from Lua GC relocation in ~200ms (was ~2.5s)
- Spanish README (README_es.md)
- Full addon UI localization: English, Russian, Spanish

### Changed / Изменено / Cambiado
- Addon architecture: switched from GetMessageInfo polling (200ms) to ChatFrame_AddMessageEventFilter (event-driven, 0ms delay)
- Buffer flush interval reduced from 1.5s to 0.5s
- Companion poll interval reduced from 500ms to 250ms
- Buffer header now includes sequence number (`__WCT_BUF_0042__`) for fast staleness check
- TOC updated for WoW Midnight (Interface: 120001, 120005)
- Dual author credit: Andrey Yumashev + Pirson

### Performance / Производительность / Rendimiento
- End-to-end latency for dictionary hits: ~2.2s → ~0.75s
- End-to-end latency for DeepL translations: ~2.5s → ~1.0s
- GetMessageInfo polling preserved as disabled fallback (`/wt poll on`)

## [1.0.8] — 2026-02-24

### Fixed / Исправлено
- Short phrases "hi", "sup", "go" now translated via phrasebook (were silently skipped due to MIN_TEXT_LENGTH and _SKIP_PHRASES filters)
- Removed "go" from detector skip list — now handled as abbreviation before detection
- Added "hi" → "привет", "sup" → "привет", "go" → "вперёд" as pre-detection abbreviations

## [1.0.7] — 2026-02-23

### Added / Добавлено
- WoW glossary: 80 safe abbreviations (9 languages) from Pirson's WoW Translator addon — instant translation of terms like aoe, dk, ilvl, gz, cc without API call
- Context-gated term expansion: 102 WoW-specific terms (dungeon names, specs, roles) expanded to plain English before DeepL when 2+ gaming terms detected in message
- Safety set: ~40 common English words (add, hit, focus, fire, arms, etc.) excluded from expansion to prevent false positives

### Fixed / Исправлено
- Overlay resize grip now works — bottom-right corner ⇡ icon is a real drag handle
- Reply translator defaults to → EN when own language is RU (was incorrectly set to → RU)
- "go?" no longer mistranslated by DeepL — added to phrasebook as "вперёд"

### Improved / Улучшено
- Memory reader: seq reset guard — prevents re-translation of already-seen messages after addon /reload (saves DeepL API quota)
- Memory reader: exponential backoff for marker-gone detection (2→4→8→16 stale reads before rescan instead of fixed 2)
- Memory reader: adaptive rescan interval (2s→5s→10s→30s) when buffer address is stable, resets to 2s on new messages
- Language detector: short Cyrillic text misdetected as Bulgarian/Ukrainian now treated as Russian (for RU users)
- NPC filter: Say/Yell messages from NPC names (containing spaces) are now filtered from overlay

## [1.0.6] — 2026-02-23

### Fixed / Исправлено
- Fixed duplicate messages flooding overlay — file watcher no longer runs alongside memory reader; WoW buffers chatlog writes for minutes then flushes a huge batch that bypassed dedup TTL
- File watcher now only activates as fallback when memory reader is unavailable (no pymem, no admin rights, WoW not running)

## [1.0.5] — 2026-02-23

### Fixed / Исправлено
- Fixed garbled binary characters (null bytes, raw memory data) appearing in translated messages — GetMessageInfo() can return strings with embedded \x00 bytes from taint corruption; now truncated at first null byte in both addon and companion
- Addon: pcall-wrapped string.find for null byte detection (safe on secret values)
- Companion: defensive payload sanitization strips null bytes and trailing control characters
- Parser: fixed `_is_item_link_only` to match color-stripped hyperlinks — item-link-only messages now correctly filtered

## [1.0.4] — 2026-02-22

### Fixed / Исправлено
- Addon: fixed `table.concat` crash on secret-tainted strings in RebuildBuffer — now pcall-filters each entry individually, skipping secret values
- Addon: concatenation with secret string produces secret result — `wctSeq .. "|RAW|" .. text` stays tainted, now handled gracefully

### Added / Добавлено
- Phrasebook: "zug zug" (orc greeting), "zamn" (slang for damn)
- Slang normalizer: "zamn" → "damn"

## [1.0.3] — 2026-02-22

### Fixed / Исправлено
- Parser: fixed "Parse returned None" for all messages — raw WoW color codes (`|cXXXXXXXX...|r`) inside player names now stripped before regex matching
- Parser: added support for `[BracketChannel] |Hplayer:...|h[Name]|h: text` format (used by Raid Warning / Объявление рейду in RU scrollback)
- Parser: added "Объявление рейду" (dative case) to channel map — RU scrollback uses dative, not genitive
- Addon: removed all dedup logic — secret string taint prevents even table indexing on concat results; companion handles dedup
- Debug console: now toggleable at runtime via Settings without restart; fixed idempotent initialization

## [1.0.2] — 2026-02-22

### Fixed / Исправлено
- Addon: fixed taint error "attempt to compare secret string" in TWW — Secret Values from GetMessageInfo are now concatenated (allowed) instead of compared (forbidden); double pcall contains taint per-frame and per-message
- Addon: removed StripMarkup on addon side — raw text with WoW markup sent to companion, companion parser handles markup stripping
- Pipeline: unmapped lingua languages (e.g. Tswana for "okay alr") now fall through to DeepL auto-detect instead of being skipped

### Added / Добавлено
- Slang normalizer: gaming slang expanded to plain English before DeepL (summ→summon, bio→break, rezz→resurrect, pls→please, etc.) — dramatically improves translation of short chat messages
- DeepL context parameter: "World of Warcraft raid group chat" hint (free, not billed)
- Phrasebook: 30+ new raid abbreviations (summ, bio, rez, cds, bl, hero, brez, wipe, kick, gl guys, gg wp, etc.)
- Version shown in overlay title bar
- "About" tab in settings with developer info, GitHub link, and donate addresses

## [1.0.1] — 2026-02-22

### Fixed / Исправлено
- Undetectable language now falls through to DeepL auto-detect instead of being skipped
- Debug console now works correctly in windowed .exe (AllocConsole + CONOUT$ redirect)
- Console hidden by default — enable via Settings → Overlay → "Show debug console"
- Added INFO-level logging for translation pipeline steps (detect, skip, translate, DeepL result)
- Fixed StreamHandler crash when sys.stderr is None in windowed exe

## [1.0.0] — 2026-02-22

First public release.

Первый публичный релиз.

### Added / Добавлено

**Core / Ядро:**
- Real-time chat translation via addon memory buffer (< 1s latency)
- Tiered memory scanning: region history (~30ms) → heap scan (~2.5s) → full scan (~7s)
- File watcher fallback — polls WoWChatLog.txt every 1s when addon unavailable
- Deduplication — messages from memory reader and file watcher are deduplicated by (author, text) with 30s TTL
- WoW item/spell link filtering — messages with only item links are skipped

**Translation / Перевод:**
- DeepL Free API integration (500K characters/month)
- Built-in phrasebook: 45 phrases (EN/RU/DE/FR/ES) + 30 gaming abbreviations — instant, no API needed
- Two-level translation cache: in-memory LRU (1000 entries) + SQLite persistent cache (7-day TTL)
- Offline language detection via lingua-py (~1ms per message)
- Cyrillic script fallback for short text that lingua can't classify
- Dual-threshold language detector: lenient (0.1) for short text (≤20 chars), strict (0.25) for longer text
- Gaming jargon auto-skip: lol, afk, brb, pull, cc, dps, heal, tank, etc.

**Overlay / Оверлей:**
- Smart overlay with WoW-native dark theme and channel colors
- Click-through mode by default (clicks pass through to the game)
- Draggable title bar, resizable from all edges
- Minimize to title bar with one click
- Channel filter tabs: All, Party, Raid, Guild, Say, Whisper, Instance
- Reply translator panel: type → translate → copy → paste in WoW
- WoW connection status indicator (attached / searching / offline)
- Translation ON/OFF toggle in title bar
- Opacity slider (20-100%)

**WoW Addon / Аддон WoW:**
- BabelChat addon (~300 lines Lua)
- ChatFrame scrollback polling every 200ms
- Ring buffer (50 messages) with `__WCT_BUF__` / `__WCT_END__` markers
- StripMarkup preserves hyperlinks while removing color codes
- `/wct` slash commands: status, buf, log, auto, flush, poll, verbose
- Auto-enable chat logging on login
- Buffer flush every 1.5 seconds

**Configuration / Настройка:**
- 5-step setup wizard for first-time configuration
- Settings dialog with 3 tabs: General, Overlay, Hotkeys
- Global hotkeys via Win32 API (default: Ctrl+Shift+T to toggle translation)
- 22 target languages supported
- One-click addon installation from settings
- Auto-detect WoW path via Windows Registry
- Debug console toggle in settings

**Infrastructure / Инфраструктура:**
- System tray integration with context menu
- PyInstaller single-file .exe build (admin privileges required)
- GitHub Actions: CI (lint + test) and Release (build .exe + GitHub Release)
- Apache-2.0 license
