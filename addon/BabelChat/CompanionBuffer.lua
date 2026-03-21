-- CompanionBuffer.lua — Memory buffer for companion app (ReadProcessMemory)
-- Ring buffer written to SavedVariable, read by BabelChat.exe via pymem.

local ADDON_NAME, addonTable = ...

-- ── Constants ────────────────────────────────────────────────
local MSG_LIMIT = 50           -- ring buffer size
local FLUSH_INTERVAL = 1.5    -- seconds between buffer flushes

-- ── State ────────────────────────────────────────────────────
local wctBuf = {}              -- accumulator table
local wctSeq = 0               -- monotonic sequence counter
local bufDirty = false
local flushTicker = nil
local logFlushTicker = nil

-- ── Dedup ───────────────────────────────────────────────
-- ChatFilter fires once per ChatFrame displaying the event.
-- 3 chat windows showing SAY = 3 calls. Dedup by (author+text).
local DEDUP_SIZE = 10
local DEDUP_TTL = 2.0  -- seconds
local dedupRing = {}   -- { key = "author\0text", time = GetTime() }
local dedupIdx = 0

local function IsDuplicate(author, text)
    local now = GetTime()
    local key = (author or "") .. "\0" .. (text or "")
    -- Check existing entries
    for i = 1, #dedupRing do
        if dedupRing[i].key == key and (now - dedupRing[i].time) < DEDUP_TTL then
            return true
        end
    end
    -- Add new entry (ring buffer)
    dedupIdx = (dedupIdx % DEDUP_SIZE) + 1
    dedupRing[dedupIdx] = { key = key, time = now }
    return false
end

-- ── Pre-allocate SavedVariable keys ──────────────────────────
-- The companion app caches the hash Node pointer for "wctbuf".
-- If the table resizes (new keys added), the Node array relocates
-- and the companion loses the pointer. So all keys must exist from start.
function addonTable.PreallocateCompanionKeys()
    local db = BabelChatDB
    if db.wctbuf == nil then db.wctbuf = "" end
    if db.wctSeq == nil then db.wctSeq = 0 end
    if db._r1 == nil then db._r1 = 0 end
    if db._r2 == nil then db._r2 = 0 end
    if db._r3 == nil then db._r3 = 0 end
    -- Restore seq counter so it survives /reload (reader tracks by seq)
    wctSeq = db.wctSeq or 0
end

-- ── Buffer rebuild ───────────────────────────────────────────
-- Concatenate ring buffer into a single string with markers.
-- Seq number embedded in header for fast staleness check:
--   __WCT_BUF_0042__\nline1\nline2\n__WCT_END__
-- Secret-tainted entries (instance chat) are silently skipped.
local function RebuildBuffer()
    local seqHeader = string.format("__WCT_BUF_%04d__", wctSeq % 10000)
    -- Include player name so companion can identify own messages
    local playerName = UnitName("player")
    local realmName = GetNormalizedRealmName() or ""
    local fullName = playerName and (playerName .. "-" .. realmName) or ""
    local result = seqHeader .. "\n0|META|PLAYER|" .. fullName
    for idx = 1, #wctBuf do
        local candidate = result .. "\n" .. wctBuf[idx]
        local ok = pcall(string.len, candidate)
        if ok then
            result = candidate
        end
    end
    result = result .. "\n__WCT_END__"
    BabelChatDB.wctbuf = result
    BabelChatDB.wctSeq = wctSeq
    bufDirty = false
end

-- ── Public API ───────────────────────────────────────────────

-- Add a chat entry to the ring buffer.
-- kind: "RAW" (needs DeepL) or "DICT" (dictionary-translated)
-- event: short event name (e.g. "SAY", "GUILD", "WHISPER")
-- author: sender name (e.g. "Thrall-Sargeras")
-- translated: dictionary-translated text (only for DICT kind)
function addonTable.BufferAddEntry(text, kind, event, author, translated)
    local db = BabelChatDB
    if not db or not db.companion or not db.companion.enabled then return end

    -- Dedup: skip if same (author, text) seen within TTL
    if IsDuplicate(author, text) then return end

    wctSeq = wctSeq + 1
    local entry
    if kind == "DICT" and translated then
        -- DICT format: SEQ|DICT|EVENT|author|original\ttranslated (tab separates original from translated)
        entry = wctSeq .. "|DICT|" .. (event or "SAY") .. "|" .. (author or "Unknown") .. "|" .. text .. "\t" .. translated
    else
        -- RAW format: SEQ|RAW|EVENT|author|text
        entry = wctSeq .. "|RAW|" .. (event or "SAY") .. "|" .. (author or "Unknown") .. "|" .. text
    end
    tinsert(wctBuf, entry)
    while #wctBuf > MSG_LIMIT do
        tremove(wctBuf, 1)
    end
    bufDirty = true
end

-- Start the periodic buffer flush ticker.
function addonTable.StartBufferFlush()
    if flushTicker then return end

    -- Initialize buffer with markers so companion can find it immediately
    if not BabelChatDB.wctbuf or BabelChatDB.wctbuf == "" then
        BabelChatDB.wctbuf = "__WCT_BUF_0000__\n__WCT_END__"
    end

    flushTicker = C_Timer.NewTicker(FLUSH_INTERVAL, function()
        if bufDirty then
            RebuildBuffer()
        end
    end)
end

function addonTable.StopBufferFlush()
    if flushTicker then
        flushTicker:Cancel()
        flushTicker = nil
    end
end

-- Chat log flush (toggle LoggingChat off/on to force WoW file buffer write)
function addonTable.StartLogFlush(interval)
    if logFlushTicker then return end
    interval = interval or 5
    logFlushTicker = C_Timer.NewTicker(interval, function()
        if LoggingChat() then
            LoggingChat(false)
            LoggingChat(true)
        end
    end)
end

function addonTable.StopLogFlush()
    if logFlushTicker then
        logFlushTicker:Cancel()
        logFlushTicker = nil
    end
end

-- Status info for slash commands
function addonTable.GetBufferStatus()
    return #wctBuf, wctSeq, MSG_LIMIT, (flushTicker ~= nil)
end

-- ── Legacy GetMessageInfo Polling (fallback) ─────────────────
-- Disabled by default — event filter is preferred.
-- Enable with /babel poll on if event filter has issues.

local POLL_INTERVAL = 0.2
local pollTicker = nil
local frameMessageCount = {}

local function PollChatFrames()
    for i = 1, NUM_CHAT_WINDOWS do
        local cf = _G["ChatFrame" .. i]
        if cf and cf:IsVisible() then
            pcall(function()
                local numMsgs = cf:GetNumMessages()
                local lastSeen = frameMessageCount[i] or 0

                if lastSeen == 0 then
                    frameMessageCount[i] = numMsgs
                elseif numMsgs > lastSeen then
                    for idx = lastSeen + 1, numMsgs do
                        pcall(function()
                            local text = cf:GetMessageInfo(idx)
                            if text then
                                local ok, nulPos = pcall(string.find, text, "\0", 1, true)
                                if ok and nulPos then
                                    text = text:sub(1, nulPos - 1)
                                end
                                addonTable.BufferAddEntry(text, "RAW")
                            end
                        end)
                    end
                    frameMessageCount[i] = numMsgs
                elseif numMsgs < lastSeen then
                    frameMessageCount[i] = numMsgs
                end
            end)
        end
    end
end

function addonTable.StartPollTimer()
    if pollTicker then return end
    pollTicker = C_Timer.NewTicker(POLL_INTERVAL, PollChatFrames)
end

function addonTable.StopPollTimer()
    if pollTicker then
        pollTicker:Cancel()
        pollTicker = nil
    end
end

function addonTable.IsPollActive()
    return pollTicker ~= nil
end
