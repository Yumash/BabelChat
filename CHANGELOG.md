# Changelog

*[По-русски](CHANGELOG_ru.md)*

All notable changes to BabelChat, newest first. Versions follow
[semantic versioning](https://semver.org/); the addon and the companion app
ship under the same number.

---

## [3.4.1] — 2026-08-26

### Fixed

- **The interface opened in Russian whatever language you had chosen.** On Linux the GTK entry point never applied the saved language at all, so the control in Settings had no effect on anything; and on a first run, before there is a choice to apply, both frontends fell back to the Russian default — so a new player anywhere in the world read the setup wizard, the first thing they see, in a language they may not have. A saved choice is honoured now, and a first run takes its language from the operating system instead, falling back to Russian when the system names one the interface does not have. Windows is asked which language its *interface* is in, which is a different setting there from the one dates and numbers are formatted by, and the one that actually answers the question.
- **Changing the language left every open window in the old one.** A widget keeps the string it was built with, so the new language reached nothing already on screen and took hold only at the next launch — which reads as a control that does nothing. The overlay relabels itself now, on both platforms, and on Windows so does the separate window the clipboard hotkey opens — created on demand and then kept, so it outlived the setting that was changed after it.
- **The tray menu was the worst of those, because you cannot close and reopen it.** It is built once at startup, and on Linux it was never translated at all: five English items above a Russian overlay, whatever you had picked. It is translated now and follows a language change on both platforms — and its first entry is written from where the overlay actually is, so it no longer offers to hide a window that is already hidden.
- **The setup wizard forgot what you had typed when you changed its language.** Showing it in a new language means building its pages again, and neither wizard kept what was already in the fields — an API key pasted on the second page, the WoW folder browsed for on the third, both silently gone because of the dropdown on the first. They carry across now.
- **Saving a new language leaves the settings window rebuilt rather than stale.** Reopening it is the rebuild, so that one save closes it; any other save leaves it where it is, with its confirmation where you can read it.

---

## [3.4.0] — 2026-08-23

### Added

- **GigaChat as the default translation provider** — free for individuals (1M tokens a year), no card, a Sber ID is enough, and it works from Russia without a VPN. This is why the release exists: DeepL's free tier asks for a card to verify identity and Microsoft needs an Azure account, and neither is reachable for a large part of the audience.
- **MyMemory as a keyless fallback** — needs no account at all, so a new player gets working translation on first launch before configuring anything, and an existing user keeps a fallback when their provider hits quota. It is available whether or not the config mentions it.
- **The Russian root certificate ships with the app.** `requests` does not read the Windows certificate store, so GigaChat could not be reached on a machine where every browser reaches it happily. The certificate is used for that one provider's session and nothing else.
- **Providers declare themselves** — adding one used to mean editing `translator.py`, `config.py`, both settings dialogs, both setup wizards and both entry points; missing one produced a backend that worked but could not be configured. A provider is now a single `ProviderSpec`, and both frontends render whatever the registry holds.
- **Two channels the app could not previously tell apart** — player-made channels and emotes each get their own toggle and their own overlay filter tab, and on the Windows overlay their own colour and prefix. The GTK overlay still draws both in Say's colour and without a badge.
- **Midnight 12.1.0 compatibility** — TOC interface versions, a brand icon, and the addon renamed to BabelChat throughout.

### Changed

- The addon's slash commands, self test and welcome frame moved to `Commands.lua`; `Core.lua` is back to wiring the addon together.
- The channel toggles are declared once and read by both settings windows, both entry points and the overlay's filter tabs. They had been five hand-written copies and had drifted in every direction.
- Three libraries the addon loaded but never called were removed.

### Fixed

- **The overlay collapses downwards.** It shrank towards its top-left, so one parked along the bottom of the screen jumped into the middle of it when minimised — the opposite of what minimising it is for. The bottom edge now stays where it is, in both directions, and the window is kept on the screen.
- **It says why chat goes quiet during a keystone run.** While a mythic key is live the game hands chat text to addons as a secret value: it reports as a string and raises on every operation, so nothing can read it, forward it or translate it. That is Blizzard's limit and there is no way around it — but the overlay simply stopping, with no word about why, was ours. The addon reports being refused and the indicator explains it, including that raids and ordinary dungeons are unaffected and that it lifts by itself.
- **The companion took a gigabyte of memory and twelve seconds to start.** The language detector was built from all seventy-five languages lingua ships, twice — 862 MB and 5.8 seconds each, measured. It is built from the twenty the app can act on now: every language it translates between, plus the Cyrillic neighbours it has to recognise in order to correct them. 517 MB and under three seconds. A language outside the list is not lost — lingua says it does not know, and an unrecognised message goes to the translation service to auto-detect, which is what it is best at.
- **The companion stopped hunting for the addon's buffer and started being handed it.** The buffer is a Lua string, so every rebuild allocates a new one somewhere else — fourteen consecutive rebuilds landed in fourteen different regions, twenty gigabytes apart, never once reusing one. Every version of this scanner has therefore paid a sweep of the heap per rebuild, and the arithmetic was brutal: the previous release burned 48% of one core and still delivered five messages a minute before going deaf. The addon now parks a constant in its saved table. A constant can be searched for at leisure, because it does not move while you look, and a Lua table's storage does not move at all while the table does not rehash — which the addon prevents by declaring every key at load. The slot holding the buffer's pointer sits beside that constant, so reading eight bytes gives the current string. Measured after: 0.10% of one core, zero sweeps, messages in the poll they were sent in.
- **The buffer carries a pulse** — a counter that ticks on every rebuild, said or unsaid. Without it a copy the addon will never write to again is indistinguishable from a quiet chat, which is what the reader kept settling on. It is also how a table left behind by a reload is spotted, in six seconds rather than three minutes.
- **The Windows scan threads run at idle priority**, as the Linux ones have since the day they were written. Nobody noticed the difference while the scan was believed to be rare.
- **Messages arrived minutes late, all at once, and then stopped.** The native scanner caches the address it found the buffer at. When Lua's garbage collector moves the buffer, the bytes left behind still parse — same markers, same last sequence — so the fast path read that ghost and never rescanned, because an idle chat looks exactly the same from there. Measured on a live session: four guild messages sent between 15:24:45 and 15:25:05 reached the app together at 15:29:06. A cached address that has produced nothing for ten seconds is now verified by a scan, and the reader separately checks whether it has run ahead of the buffer, which it could not recover from before: the sequence filter lives inside the scanner, so a buffer behind our position was invisible.
- **A refusal is no longer shown as a translation.** GigaChat answers 200 with a paragraph about what it will not discuss, and that paragraph went into the overlay where the translation belongs. It is recognised now — by wording and by length together, so a genuine translation mentioning language models is not caught — reported as a failure so the next provider gets a turn, and if none succeeds the line says so in four words.
- **Belarusian is treated as Russian**, alongside Bulgarian and Ukrainian. lingua reads short Russian words as Belarusian, and one of them was sent to a translation service, which then refused it.
- **The colour escape The War Within added is stripped.** `|cnIQ4:` — colour by name rather than by hex — is what a keystone link carries, and the overlay showed it verbatim in front of the link text.
- **A player-made channel is translated by default now.** Its toggle inherited General's, and General is off — so joining a channel, typing in it and getting nothing was the documented behaviour. The reasoning for keeping it off was that these channels are private; whispers and guild chat are more private still and have always been on, so that argument does not hold. Trade and General stay off: you are in those whether you like it or not.
- **A channel that is switched off says so.** The reason a message vanished was logged at DEBUG, behind a console that is off by default. It is a warning now, once per channel, naming the channel and not the message.
- **The reader stopped accusing a working addon.** Both scanners return the same answer for "no buffer here" and "nothing newer than you already have", so any quiet minute looked like a broken addon — including the minute after it had handed over the player's name. The complaint is only raised when the buffer has never been found since attaching.
- **The in-game gloss was the headline complaint, and it was six separate defects.** The same arrow glyph meant both "annotation follows" and "translates to"; a term repeated once per occurrence; entries followed the dictionary's hash order rather than the sentence's; alternatives printed verbatim ("Спасибо/спс"); a newline doubled the height of every glossed message and broke copy-chat; and the addon and the overlay both answered the same message in different words. The gloss is now `term = meaning` pairs on the same line, in message order, one per term, capped at three, and it stays quiet while the companion app is running.
- **The gloss was written in Spanish.** `targetLocale` defaulted to `esES` — inherited from the addon this dictionary came from — and the auto-detection meant to correct it compared against `enUS`, so it never fired. The language now comes from the WoW client, and a saved config still carrying the old default is corrected unless the client is actually Spanish. The companion had the same inheritance: `target_language` defaulted to `ES` while the interface and the user's own language both defaulted to `RU`.
- **Russian punctuation stopped the dictionary matching.** Word boundaries were decided one byte at a time and every byte above 127 counted as a letter, so guillemets, the em dash, the ellipsis and the non-breaking space each glued themselves to the word beside them. Lua's `string.lower` is ASCII-only, so a sentence opening with "Спс" never met the key "спс".
- **Punctuation between two terms lost both of them** — `dps/heal`, `gg,wp` and `brb/afk` are the ordinary shape of an LFG line and none of them glossed.
- **Channels were classified by name, so on a Russian client the Trade toggle did nothing** and the General toggle controlled Trade. Classification now uses `zoneChannelID`, which is the same number on every locale. A player-made channel reports id 0 and is classified as Custom rather than being passed off as General.
- **A GigaChat key was refused with a bare `http_400`.** The project page shows three values, and the "authorization key" is the longest and the most key-looking of them, so it landed in the field marked *secret* — where the app encoded it a second time and sent a header the server could not read. The key is now accepted in either field, and the two quite different causes of a 400 are told apart: a credential the server cannot decode, and a project on the corporate tariff. A key that is merely wrong answers 401, not 400.
- **The first-run wizard could not save a provider.** Entering its final page raised, and the only code path that writes the credentials sits behind that page — so on a fresh install a provider could not be configured through the wizard at all.
- **Other players' chat was written to disk by default**, and message text was quoted in the application log at INFO. The capture trace is now opt-in, off by default, and the checkbox says what the file contains.
- **The native scanner was loaded by bare filename**, which sends Windows through its standard search order — the working directory and every entry in PATH included. Every candidate is now an absolute path, and the build no longer requests administrator rights: `ReadProcessMemory` against a same-user process never needed them, and standing elevation turned an ordinary DLL-planting bug into a privilege escalation.
- **Secret chat values and hostile message text could break capture.** Under chat messaging lockdown, instance chat arguments raise on ordinary string operations; a single unguarded one took the chat filter down for the rest of the session. Message text is written by other players and could forge the buffer's own end marker.
- **Emotes and yells stopped being translated on upgrade.** Both used to arrive through the Say toggle; giving them their own switch would have taken them away in silence, so an existing config inherits its Say setting for both. Player-made channels were given the same treatment at first and it turned out to be wrong; see above.
- **Three channel switches were decoration.** Yell had a checkbox on both platforms that nothing read, next to a second box that already covered it. Custom and Emote were saved by the Linux settings window and dropped by the Linux entry point.
- **The settings window was half in English** for every Russian-speaking user, and the Linux one rendered raw string-table keys where field labels belong. Language names are now written in each language itself.
- **Section headings overlapped the controls beneath them** in the in-game options panel, and the category names were the Spanish ones the dictionary came from.
- **CI had been red on every run, and not because of the code.** The native scanner is a build artefact that nothing in the workflow built, two test dependencies were never declared so 29 tests silently turned into skips there, and the test-count floor was taken from a developer machine that collected fifty more tests than CI could.
- **Starting the app could terminate an unrelated program.** Only one copy should run, so startup killed whatever process the lock file named — and the lock file named a bare PID, which the operating system hands back out to something else once the process it belonged to is gone. On a machine that had been rebooted since the last run, that number could be anything: a browser, a game, the editor the user was working in. The lock now records when the process started as well, and nothing is terminated unless both match.

### Tests

- **168 → 873.** The addon's Lua is exercised under a real Lua 5.1 interpreter through `lupa` — the same version WoW runs — rather than being re-implemented in Python.
- **The test harness was quietly making every Cyrillic assertion meaningless.** Lua's `string.lower` and its `%w`/`%s` classes read the process C locale, and under `Russian_Russia.1252` two distinct Cyrillic letters fold to the same bytes while the trail byte of "Р" matches `%s`. WoW runs under the C locale; the harness now pins it.
- **A set of tests could not fail and have been rewritten**, each confirmed by reintroducing the defect it names. The settings panel is now built with a recording `CreateFrame` instead of being matched against its own source text, and the dictionary is tested against the data that actually ships on lines players type.
- **A dependency guard now stops a test from being silently switched off.** Every module behind `pytest.importorskip` has to be installed and named in `requirements.txt`, or listed with the reason it cannot be.
- The TOC's `SavedVariables` line and its file load order are pinned, and every addon file is syntax-checked.

---

## [3.3.0] — 2026-07-25

### Added

- **Native GTK4 overlay for Linux (Wayland)** — the Linux frontend is rebuilt in GTK4 + gtk4-layer-shell, rendering as a true layer-shell surface that stays above fullscreen WoW without XWayland workarounds. Windows continues to use the PyQt6 frontend unchanged (see `ARCHITECTURE_FRONTENDS.md`).
  - Per-channel chat filtering, streaming messages with channel badges
  - Drag/resize with ghost outline preview
  - Quick translation on/off toggle and reply-language selector
  - Settings window with live apply — no restart needed
  - First-run setup wizard (GTK)
- **Linux packages: AppImage, `.deb` and `.rpm`** — the release now builds all three on `ubuntu-24.04` and attaches them to the GitHub Release. Each artefact is verified by installing it into a clean `debian:13` / `ubuntu:24.04` / `fedora:41` container and confirming it links and reaches GTK init — not by the fact that it built.
- **Automatic backend fallback** — if your priority backend (DeepL or Microsoft) fails or hits quota, the other configured backend is tried automatically instead of dropping the message.
- **New chat channels** — Trade, General and Services are now captured, filterable and translated end to end (addon + app).
- `packaging/` with `babelchat.desktop` and a fish build script (`build-linux.fish`) that produces a self-contained Linux AppImage (Rust scanner → PyInstaller → linuxdeploy + GTK bundling).

### Changed

- Merged upstream 3.2.0: Endgame/Midnight dictionary category, `discord.gg` link fix, dictionary engine pre-indexing, release workflow and lint fixes.
- Removed the unused `lang_selector.py` / `reply_widget.py` modules — reply-language selection lives inline in both overlays.
- `ruff check app/` is fully clean, including the new GTK modules.

### Fixed

- **The Linux build did not run off a clean machine** — three defects that only surfaced without the GTK4 dev packages installed, so a developer's box never showed them:
  - the GTK4 core typelibs (`Gtk-4.0`, `Gdk-4.0`, `Graphene-1.0`, `Gsk-4.0`) were never bundled, and the app died with `Namespace Gtk not available`;
  - the bundled `libgtk4-layer-shell` was staged under a name the loader never tried, and its `LD_LIBRARY_PATH` was set in an AppRun hook linuxdeploy does not source, so the AppImage could not load layer-shell;
  - `overlay_gtk` crashed at import when gtk4-layer-shell was absent instead of falling back to X11/plain, contradicting its own fallback path.
- **Windows: high CPU while chat was idle** — losing the buffer address during idle no longer triggers continuous full memory scans; scans are rate-limited with a tri-state fast path in both Rust scanners.
- Saving settings no longer resets the translation toggle.

### Tests

- Restored 124 unit tests covering the translation core (parser, pipeline, cache, glossary, phrasebook, dedup) that a snapshot import had silently deleted, taking coverage of `app/` from 2% back to 18%.
- CI now fails when the test suite shrinks — a test-count floor guards against the same silent loss recurring.

---

## [3.2.0] — 2026-06-15

### Added

- **Endgame & Midnight dictionary category** — 22 current terms across all 14 client languages (delves, Bountiful, Brann, Mythic+/keystone/affixes, gear tracks Champion/Hero/Myth, Gilded/Runed crests, Warband, catalyst, spark, renown, Raider.IO, KSM, Manaforge Omega, Undermine). The in-game dictionary now keeps up with The War Within / Midnight chat.
- **Dictionary engine**: LibBabble zone/item-set lookups are pre-indexed at rebuild time instead of re-scanned on every chat line; single-word matching now resolves the correct token position when a word repeats in a message.
- **Clearer onboarding** (from CurseForge feedback) — the first-run welcome now states the dictionary works instantly and free with no app required; the companion setup explains that DeepL's free tier asks for a credit card to verify (never charges) while Microsoft Translator needs no card. The CurseForge description was rewritten with a Quick Start.
- `babelchat_scanner/` — a Rust crate producing `libbabelchat_scanner.so` for Linux.
- `build-linux.spec` — bundles `libbabelchat_scanner.so` into the Linux binary via PyInstaller.

### Changed

- `memory_reader_linux.py` is now a thin Python wrapper around the Rust scanner, falling back to pure Python when the `.so` is missing.
- The Linux architecture diagram in the README reflects the Rust scanner.
- The limitations section no longer mentions the 5–10s relocation delay; it no longer applies.

### Fixed

- **Discord invite links are no longer mistranslated** — schemeless links like `discord.gg/xyz` reached DeepL, which read `.gg` as the gaming abbreviation and rendered it as "good game". URL tokenization now also protects known link and invite domains (`discord.gg`, `t.me`, `bit.ly`, …) and any `domain.tld/path`.

### Performance

**The Linux memory scanner was rewritten in Rust** — the single biggest performance improvement since Linux support was added.

- The Rust scanner library (`libbabelchat_scanner.so`) replaces the pure-Python `/proc/<pid>/mem` scanner.
- It uses `process_vm_readv` rather than `/proc/<pid>/mem` — a dedicated cross-process memory syscall that does not go through the VFS layer, needs no file descriptor and does not pause the target process. This eliminates the WoW frame-time stutters the old approach caused.
- **Address cache** — steady-state polling (every 250ms) is a single `process_vm_readv` call at the cached address, costing microseconds and near-zero CPU.
- A full parallel heap scan (Rayon, 2 threads) runs only on a cache miss, which happens roughly every 14s when the Lua GC relocates the buffer.
- Scanner threads run at `SCHED_IDLE` — the lowest Linux scheduling class, below `nice +19`. WoW, the compositor and every other process take absolute priority over the scanner.
- Initial scan time: 10–13s → ~2.5s.
- GC relocation detection: 14–17s gaps → ~2s.
- End-to-end overlay latency: many seconds → ~1s (the floor is the DeepL API round trip).
- Game stutters: eliminated.

The addon's flush interval dropped from 1.5s to 0.25s — messages reach memory within one poll cycle of arriving, cutting the addon's share of the latency from up to 1.5s to about 250ms.

The Python scanner, retained as a fallback when the `.so` is absent, was overhauled alongside it:

- a persistent `/proc/<pid>/mem` file descriptor, removing an `open`/`close` pair from every read;
- regions scanned smallest first — active Lua strings live in smaller allocations, so the buffer is found sooner;
- an early exit on the first valid marker rather than scanning every remaining region;
- ghost buffer blacklisting — stale copies that cause seq resets are blacklisted immediately;
- every rescan path passes `min_seq`, so only buffers newer than the already-delivered messages are accepted;
- the rescan interval no longer backs off exponentially when no newer buffer is found;
- the background scanner thread validates seq before committing a new address.

---

## [3.1.2] — 2026-05-31

### Added

- **Linux/Proton support** — the companion app runs on Linux (CachyOS, Arch, Ubuntu and others) with WoW under Proton/Wine. Tested on CachyOS.
- A Linux memory reader (`memory_reader_linux.py`) reading WoW process memory through `/proc/<pid>/mem` and `os.pread()`, with full 64-bit address support — Wine and Proton allocate above 4GB.
- Linux hotkeys (`hotkeys_linux.py`) — global hotkeys through `pynput`, degrading gracefully on pure Wayland.
- Platform dispatchers — `memory_reader.py` and `hotkeys.py` select the right implementation from `sys.platform`.
- `config.py`: Linux WoW path detection (`~/.steam/`, `/run/media/`) alongside the Windows registry lookup.
- `main.py` and `overlay.py`: every Windows-only call (`ctypes.windll`, `X11BypassWindowManagerHint`) is guarded by a `sys.platform` check.
- `overlay.py`: the `X11BypassWindowManagerHint` flag on Linux, for always-on-top and a free `move()` through XWayland.
- `requirements.txt`: `pymem` is Windows-only; `pynput` added for Linux.
- `build.spec`: Linux modules are excluded from the Windows `.exe` build.

### Notes

- Linux needs `ptrace_scope=0`: `echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope`.
- Run with `QT_QPA_PLATFORM=xcb` for an always-on-top, draggable overlay on Wayland.
- Enable the companion in WoW once: `/run BabelChatDB.companion = {enabled = true}`.
- Message latency on Linux is 5–10s higher than on Windows because of Lua GC buffer relocation — a known limitation of the `/proc/mem` approach.

---

## [3.1.1] — 2026-03-25

### Changed

- **Code cleanup:** 235 lines of dead pointer-chasing code removed from the memory reader.
- `DeduplicationBuffer` extracted into a class of its own, with a 10,000-entry safety cap.
- Over 40 magic numbers replaced by named constants across the pipeline, the overlay and the memory reader.
- Five duplicated scan-accept blocks unified into an `_accept_marker()` helper.
- Named regex groups in the parser (`m.group('text')` rather than `m.group(4)`).
- A race fixed: `itertools.count()` for thread-safe message ids.
- Exception handlers narrowed (`RuntimeError | OSError` rather than a bare `Exception`).
- Dead `dict_text` parameter, a duplicate regex and unused variables removed.
- `RE_WOW_LINK` made public — it had been private and imported across modules behind a `noqa`.

---

## [3.0.1] — 2026-03-20

### Added

- Renamed the project: ChatTranslatorHelper → **BabelChat**. A new identity, and no CurseForge conflict.
- A slang dictionary category — 33 new terms: ez, copium, bricked, pumping, carry, wipe, lust, pug, soak, kite, gank, glad…
- The `/babel` slash command, replacing `/wt`.
- CurseForge packaging: `.pkgmeta`, an addon README, a BBCode description and a separate `BabelChat-Addon.zip` in releases.
- Automatic database migration from the old ChatTranslatorHelper on first load.
- Technical documentation (`docs/tech/`) and a user guide (`docs/user/`).

### Fixed

- **Critical:** a race in deduplication — `_recent_messages` was reached from several threads with no lock, and is now protected by a `threading.Lock`.
- **Critical:** an overlay memory leak — the `_messages` list and the QTextEdit grew without bound over a long session, and are now capped at 500 and 1500.
- Torn config reads — the pipeline thread could see a mixture of old and new values, and now works from a snapshot.
- A translator crash on network errors — only `DeepLException` was caught; a general fallback was added.
- The SQLite cache was never cleaned up — `cleanup()` now runs when the pipeline starts, removing expired entries.
- A corrupt or missing config was silently replaced by the defaults; it now logs a warning.
- Dedup timestamps used `time.time()`, which NTP can move; they use `time.monotonic()` now.
- An empty payload from the addon buffer caused wasted work and is skipped early.

---

## [3.0.0] — 2026-03-20

### Added

- Streaming translation — the original message appears in the overlay at once and the translation arrives 0.5–2s later.
- A thread-safe translation cache with an explicit `threading.Lock`; it had been relying on the GIL.
- Atomic config saving — a temporary file plus `os.replace()`, a `.bak` backup and automatic recovery from corrupt JSON.
- Seq freshness tracking — a frozen (zombie) buffer is detected from a three-poll seq history and triggers a rescan.
- A 60-second blacklist TTL — zombie addresses expire and are scanned again once the GC has reclaimed the memory.
- DictEngine v2: a clean annotation line below the original rather than inline colour spam.
- Hyperlink-aware dictionary matching — `|H...|h` and `|cff...|r` blocks are skipped.
- An overlap guard, preventing a dictionary term from being matched twice.
- 28 new tests (105 → 133): pipeline end-to-end (8) and parser robustness (20).

### Changed

- The DICT buffer separator changed from a pipe to a tab, which fixes parsing when WoW colour codes contain pipes.
- The pipeline checks `translation_enabled` before processing the text, so a disabled translation exits early.
- `parse_addon_line` handles the v2.1 format with its RAW/DICT kind field.

### Fixed

- SQLite ran with `check_same_thread=False` and no lock; it is protected by a `threading.Lock` now.
- Config corruption on a crash — atomic writes prevent a partial file.
- DICT messages carrying WoW colour codes broke the parser through the pipe in `|cffXXXXXX...|r`.
- DictEngine matched inside WoW hyperlinks (`|Hitem:...|h[Name]|h|r`).
- Overlapping DictEngine matches produced duplicated translations.

---

## [2.2.2] — 2026-03-19

### Added

- A parallel heap scan: eight-thread `ReadProcessMemory` through a `ThreadPoolExecutor`, covering 4000+ memory regions at once.
- A "don't translate my own messages" option in Settings → Overlay, with the player name detected from the addon's META.
- Spanish interface translations — 153 strings, covering the overlay and the settings in full.
- A "Why Python?" section in the README, explaining the architecture choice.
- An NPC message filter in the chat history — names with spaces in the Say and Yell channels.
- WoW colour codes stripped from the addon's dictionary translations.

### Changed

- The DICT translation bypass — the addon dictionary is disabled while the companion runs, and every message goes through DeepL for consistent quality.
- The dedup TTL rose from 30s to 60s, preventing duplicates from zombie copies of the Lua buffer.
- The smart rescan threshold dropped from 3s to 1.5s, detecting a moved buffer sooner.
- Rescan intervals shortened to [2, 3, 5, 10]s from [2, 5, 10, 30]s.
- The quick-to-full rescan threshold dropped to two misses from five.

### Fixed

- A dedup bug on a seq reset — texts were saved from the *new* buffer rather than from the delivered messages, so every message after a `/reload` was skipped.
- The player name property was missing from the `MemoryChatWatcher` wrapper class.
- A lazy import of `clean_message_text` crashed the pipeline.

### Performance

- About half of all messages are delivered instantly through a quick rescan (0–31ms).
- The other half arrive through a heap scan (2.5–3.8s), limited by memory bandwidth at 3.3GB.
- A pointer-chasing prototype was implemented and left disabled; it needs research into WoW's Lua internals.

---

## [2.1.0] — 2026-03-18

### Added

- Addon buffer format v2.1: `SEQ|KIND|EVENT|author|text`, with DICT adding `|translated`.
- Deduplication in `BufferAddEntry` (author plus text, 2s TTL), fixing triplicate messages from several ChatFrames.
- The addon buffers every channel regardless of the `dict.channels` filter.
- The pipeline shows DICT messages with their dictionary translation, without calling DeepL.
- The pipeline shows RAW messages in your own language untranslated, for conversation context.
- A single-instance guard through a PID lock file (`wct.lock`) with `TerminateProcess`.
- A zombie marker blacklist in the memory reader.
- Spanish localisation in `Locales.lua`, covering esES and esMX.

### Changed

- The version was raised to 2.1.0 across the TOC, `Core.lua`, `Config.lua` and `about_dialog.py`.

---

## [2.0.0] — 2026-03-16

### Added

- Pirson's WoW Translator dictionary engine merged in — 313 WoW terms in 14 languages, with inline chat translation.
- LibBabble integration — over 5000 localised zone names, item sets, races and classes.
- An addon settings panel in WoW (Interface → AddOns → Chat Translator) with category toggles, channel filters, a language picker and a colour picker.
- A minimap button for quick access to the settings.
- A companion app toggle, enabling or disabling the memory buffer for the overlay independently.
- DICT/RAW message tagging, so the companion skips the DeepL API for dictionary-matched messages.
- A neighbourhood scan — the memory reader recovers from a Lua GC relocation in about 200ms rather than 2.5s.
- A Spanish README (`README_es.md`).
- Full addon interface localisation: English, Russian and Spanish.

### Changed

- Addon architecture: `GetMessageInfo` polling every 200ms gave way to `ChatFrame_AddMessageEventFilter`, which is event-driven and adds no delay.
- The buffer flush interval dropped from 1.5s to 0.5s.
- The companion poll interval dropped from 500ms to 250ms.
- The buffer header carries a sequence number (`__WCT_BUF_0042__`) for a fast staleness check.
- The TOC was updated for WoW Midnight (Interface 120001, 120005).
- Dual author credit: Andrey Yumashev and Pirson.

### Performance

- End-to-end latency for dictionary hits: ~2.2s → ~0.75s.
- End-to-end latency for DeepL translations: ~2.5s → ~1.0s.
- `GetMessageInfo` polling is kept as a disabled fallback (`/wt poll on`).

---

## [1.0.8] — 2026-02-24

### Fixed

- Short phrases — "hi", "sup", "go" — are translated through the phrasebook again; the `MIN_TEXT_LENGTH` and `_SKIP_PHRASES` filters had been dropping them silently.
- "go" was removed from the detector's skip list and is handled as an abbreviation before detection.
- "hi", "sup" and "go" were added as pre-detection abbreviations.

---

## [1.0.7] — 2026-02-23

### Added

- A WoW glossary: 80 safe abbreviations in nine languages, from Pirson's WoW Translator addon — terms like aoe, dk, ilvl, gz and cc translate instantly with no API call.
- Context-gated term expansion: 102 WoW-specific terms (dungeon names, specs, roles) are expanded to plain English before DeepL sees them, once two or more gaming terms appear in a message.
- A safety set of about 40 common English words (add, hit, focus, fire, arms and so on) excluded from expansion, to prevent false positives.

### Changed

- Memory reader: a seq reset guard prevents re-translating messages already seen after an addon `/reload`, which saves DeepL quota.
- Memory reader: exponential backoff for marker-gone detection — 2, 4, 8 then 16 stale reads before a rescan, rather than a fixed 2.
- Memory reader: an adaptive rescan interval (2s, 5s, 10s, 30s) while the buffer address is stable, reset to 2s on a new message.
- Language detector: short Cyrillic text misread as Bulgarian or Ukrainian is treated as Russian for Russian-speaking users.
- NPC filter: Say and Yell messages from NPC names, which contain spaces, are kept out of the overlay.

### Fixed

- The overlay resize grip works — the bottom-right corner is a real drag handle.
- The reply translator defaults to English when your own language is Russian; it had been set to Russian.
- "go?" is no longer mistranslated by DeepL; it is in the phrasebook.

---

## [1.0.6] — 2026-02-23

### Fixed

- Duplicate messages flooding the overlay: the file watcher no longer runs alongside the memory reader. WoW buffers chat-log writes for minutes and then flushes a large batch at once, which slipped past the dedup TTL.
- The file watcher activates only as a fallback, when the memory reader is unavailable — no pymem, no administrator rights, or WoW not running.

---

## [1.0.5] — 2026-02-23

### Fixed

- Garbled binary characters — null bytes and raw memory — appearing in translated messages. `GetMessageInfo()` can return strings with embedded null bytes from taint corruption; both the addon and the companion now truncate at the first one.
- Addon: `string.find` is wrapped in `pcall` for null-byte detection, which is safe on secret values.
- Companion: payload sanitisation strips null bytes and trailing control characters.
- Parser: `_is_item_link_only` matches colour-stripped hyperlinks, so a message holding nothing but an item link is filtered correctly.

---

## [1.0.4] — 2026-02-22

### Added

- Phrasebook: "zug zug" (the orcish greeting) and "zamn".
- Slang normaliser: "zamn" → "damn".

### Fixed

- Addon: a `table.concat` crash on secret-tainted strings in `RebuildBuffer`. Each entry is now filtered individually through `pcall`, skipping secret values.
- Addon: concatenating with a secret string produces a secret result, so `wctSeq .. "|RAW|" .. text` stays tainted. That is handled gracefully now.

---

## [1.0.3] — 2026-02-22

### Fixed

- Parser: "Parse returned None" for every message — raw WoW colour codes inside player names are stripped before the regex runs.
- Parser: support for the `[BracketChannel] |Hplayer:...|h[Name]|h: text` format, used by Raid Warning in Russian scrollback.
- Parser: "Объявление рейду" added to the channel map — Russian scrollback uses the dative case, not the genitive.
- Addon: all dedup logic removed. Secret string taint prevents even indexing a table with the result of a concatenation, so the companion handles dedup.
- Debug console: it can be toggled at runtime from the settings without a restart, and its initialisation is idempotent.

---

## [1.0.2] — 2026-02-22

### Added

- Slang normaliser: gaming slang is expanded to plain English before DeepL (summ → summon, bio → break, rezz → resurrect, pls → please and so on), which improves short chat messages considerably.
- A DeepL context parameter: the hint "World of Warcraft raid group chat", which is free and not billed.
- Phrasebook: over 30 new raid abbreviations — summ, bio, rez, cds, bl, hero, brez, wipe, kick, gl guys, gg wp and others.
- The version is shown in the overlay title bar.
- An "About" tab in the settings, with developer information, a GitHub link and donation addresses.

### Fixed

- Addon: the taint error "attempt to compare secret string" on The War Within. Secret values from `GetMessageInfo` are concatenated, which is allowed, rather than compared, which is not; a double `pcall` contains the taint per frame and per message.
- Addon: `StripMarkup` was removed from the addon side. Raw text with WoW markup goes to the companion, whose parser strips it.
- Pipeline: an unmapped lingua language — Tswana for "okay alr", say — falls through to DeepL's auto-detection rather than being skipped.

---

## [1.0.1] — 2026-02-22

### Fixed

- An undetectable language falls through to DeepL auto-detection rather than being skipped.
- The debug console works in the windowed `.exe` (`AllocConsole` plus a `CONOUT$` redirect).
- The console is hidden by default and enabled from Settings → Overlay → "Show debug console".
- INFO-level logging was added for the pipeline steps: detect, skip, translate, DeepL result.
- A `StreamHandler` crash when `sys.stderr` is None in a windowed executable.

---

## [1.0.0] — 2026-02-22

First public release.

### Added

**Core**

- Real-time chat translation through the addon's memory buffer, under a second of latency.
- Tiered memory scanning: region history (~30ms), then a heap scan (~2.5s), then a full scan (~7s).
- A file watcher fallback, polling `WoWChatLog.txt` every second when the addon is unavailable.
- Deduplication — messages from the memory reader and the file watcher are deduplicated by author and text with a 30-second TTL.
- WoW item and spell link filtering — a message holding nothing but links is skipped.

**Translation**

- DeepL Free API integration (500,000 characters a month).
- A built-in phrasebook: 45 phrases in English, Russian, German, French and Spanish, plus 30 gaming abbreviations — instant, with no API call.
- A two-level translation cache: an in-memory LRU of 1000 entries over a persistent SQLite cache with a seven-day TTL.
- Offline language detection through lingua-py, about a millisecond per message.
- A Cyrillic-script fallback for short text lingua cannot classify.
- A dual-threshold detector: lenient (0.1) for text of 20 characters or less, strict (0.25) above that.
- Gaming jargon skipped automatically: lol, afk, brb, pull, cc, dps, heal, tank and the rest.

**Overlay**

- A smart overlay with a WoW-native dark theme and per-channel colours.
- Click-through by default, so clicks reach the game.
- A draggable title bar, resizable from every edge.
- Minimise to the title bar in one click.
- Channel filter tabs: All, Party, Raid, Guild, Say, Whisper, Instance.
- A reply translator panel: type, translate, copy, paste into WoW.
- A WoW connection indicator: attached, searching or offline.
- A translation on/off toggle in the title bar.
- An opacity slider, 20% to 100%.

**WoW addon**

- The BabelChat addon, about 300 lines of Lua.
- ChatFrame scrollback polling every 200ms.
- A 50-message ring buffer with `__WCT_BUF__` and `__WCT_END__` markers.
- `StripMarkup` preserves hyperlinks while removing colour codes.
- `/wct` slash commands: status, buf, log, auto, flush, poll, verbose.
- Chat logging enabled automatically on login.
- A buffer flush every 1.5 seconds.

**Configuration**

- A five-step setup wizard for the first run.
- A settings dialog with three tabs: General, Overlay and Hotkeys.
- Global hotkeys through the Win32 API; Ctrl+Shift+T toggles translation by default.
- 22 target languages.
- One-click addon installation from the settings.
- The WoW path detected from the Windows registry.
- A debug console toggle in the settings.

**Infrastructure**

- System tray integration with a context menu.
- A single-file PyInstaller `.exe` build, requiring administrator rights.
- GitHub Actions for CI (lint and test) and for releases (build the `.exe`, publish a GitHub Release).
- The Apache-2.0 licence.
