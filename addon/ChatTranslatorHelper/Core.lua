-- ChatTranslatorHelper: capture chat for WoWTranslator companion app
-- Reads ChatFrame scrollback via GetMessageInfo() — no taint issues.
-- All translation logic is in the companion app.

local ADDON_NAME = "ChatTranslatorHelper"
local frame = CreateFrame("Frame")

-- SavedVariables defaults
ChatTranslatorHelperDB = ChatTranslatorHelperDB or {
    autoLog = true,
    verbose = true,
    flushInterval = 5,  -- seconds between LoggingChat toggle flushes
}

-- Pre-allocate ALL table keys on load to prevent hash table resize.
-- The companion app locates the hash Node for "wctbuf" once, then reads
-- its pointer every 500ms (O(1)).  If the table resizes (new keys added),
-- the Node array is reallocated and the companion loses the pointer.
-- So we ensure every possible key exists from the start.
local function PreallocateKeys()
    local db = ChatTranslatorHelperDB
    if db.wctbuf == nil then db.wctbuf = "" end
    if db._r1 == nil then db._r1 = 0 end
    if db._r2 == nil then db._r2 = 0 end
    if db._r3 == nil then db._r3 = 0 end
end
PreallocateKeys()

-- Flush timer handle
local flushTicker = nil

-- ── Memory Buffer for Companion App ──────────────────────────
-- Ring buffer read by companion via ReadProcessMemory.
-- Format: SEQ|RAW|formatted_chat_line
local MSG_LIMIT = 50  -- ring buffer size
local wctBuf = {}      -- accumulator table
local wctSeq = 0       -- monotonic sequence counter

local function Print(msg)
    if ChatTranslatorHelperDB.verbose then
        print("|cFFFFD200[WCT]|r " .. msg)
    end
end

-- Force flush the chat log buffer by toggling LoggingChat off/on.
local function FlushChatLog()
    if LoggingChat() then
        LoggingChat(false)
        LoggingChat(true)
    end
end

local function StartFlushTimer()
    if flushTicker then return end
    local interval = ChatTranslatorHelperDB.flushInterval or 5
    flushTicker = C_Timer.NewTicker(interval, FlushChatLog)
    Print("Chat log flush every " .. interval .. "s enabled.")
end

local function StopFlushTimer()
    if flushTicker then
        flushTicker:Cancel()
        flushTicker = nil
    end
end

local bufDirty = false

local function RebuildBuffer()
    -- Build buffer via sequential string concat.
    -- Some entries are secret-tainted (from GetMessageInfo in instances).
    -- table.concat crashes on secrets; plain concat succeeds but propagates
    -- taint to the result.  A tainted result string will then cause
    -- table.concat to fail on subsequent operations.
    --
    -- Strategy: concat each entry one by one.  After each concat, verify
    -- the result is not tainted by calling string.len() inside pcall.
    -- string.len() crashes on secret strings but succeeds on normal ones.
    -- If the result is tainted, discard it and keep the previous clean result.
    local result = "__WCT_BUF__"
    for idx = 1, #wctBuf do
        local candidate = result .. "\n" .. wctBuf[idx]
        -- Check if candidate is tainted: string.len raises on secrets
        local ok = pcall(string.len, candidate)
        if ok then
            result = candidate
        end
        -- If not ok: entry was secret, skip it silently
    end
    result = result .. "\n__WCT_END__"
    ChatTranslatorHelperDB.wctbuf = result
    bufDirty = false
end

local function AddEntry(entry)
    tinsert(wctBuf, entry)
    while #wctBuf > MSG_LIMIT do
        tremove(wctBuf, 1)
    end
    bufDirty = true
end

-- Flush dirty buffer to SavedVariables string periodically.
-- Each RebuildBuffer() creates a NEW Lua string at a NEW memory address
-- (Lua strings are immutable).  The companion caches the memory region
-- and rescans it on stale (~50-200ms), so moderate flush interval is fine.
local FLUSH_INTERVAL = 1.5  -- 1.5s — companion rescans every 2s, so keep fresh
C_Timer.NewTicker(FLUSH_INTERVAL, function()
    if bufDirty then
        RebuildBuffer()
    end
end)

-- ── ChatFrame Scrollback Polling ──────────────────────────────
-- Instead of hooking AddMessage (which doesn't fire for player chat
-- in TWW 12.0 due to secure C++ path), we poll the ChatFrame's
-- scrollback buffer using GetNumMessages() / GetMessageInfo().
-- This reads already-rendered text — no taint issues.
-- Used by BasicChatMods, Prat, and other chat addons in TWW.

local POLL_INTERVAL = 0.2  -- 200ms between polls
local pollTicker = nil

-- Track how many messages we've seen per ChatFrame
local frameMessageCount = {}  -- frameIndex -> last known GetNumMessages()

-- Dedup: same message text may appear in multiple ChatFrames (tabs)
-- Store last 100 cleaned texts to avoid duplicate entries
local recentTexts = {}  -- text -> true
local recentTextsList = {}  -- ordered list for eviction
local DEDUP_LIMIT = 100

local function StripMarkup(text)
    if not text then return "" end
    local s = text
    s = s:gsub("|c%x%x%x%x%x%x%x%x", "")
    s = s:gsub("|r", "")
    s = s:gsub("|T.-|t", "")
    s = s:gsub("|A.-|a", "")
    return strtrim(s)
end

local function PollChatFrames()
    for i = 1, NUM_CHAT_WINDOWS do
        local cf = _G["ChatFrame" .. i]
        if cf and cf:IsVisible() then
            -- Wrap per-frame processing in pcall: In TWW 12.0, chat
            -- messages inside instances are "Secret Values".  Direct
            -- comparison (==, ~=, <, >) on secrets raises a Lua error,
            -- but concatenation and string.format WORK with secrets.
            -- So we avoid ALL comparisons on text and just concatenate
            -- it straight into the buffer entry.  The companion app
            -- handles StripMarkup + dedup + empty-check on its side.
            pcall(function()
                local numMsgs = cf:GetNumMessages()
                local lastSeen = frameMessageCount[i] or 0

                if lastSeen == 0 then
                    frameMessageCount[i] = numMsgs
                elseif numMsgs > lastSeen then
                    for idx = lastSeen + 1, numMsgs do
                        -- In TWW 12.0, GetMessageInfo may return Secret
                        -- Values.  ANY operation on a secret (comparison,
                        -- table indexing, even concat result used as table
                        -- key) can raise a taint error.  So we do the
                        -- absolute minimum: concat seq + text into a single
                        -- string and AddEntry.  No dedup, no checks —
                        -- companion handles all of that.
                        pcall(function()
                            local text = cf:GetMessageInfo(idx)
                            if text then
                                -- Try to strip embedded null bytes (taint
                                -- corruption).  string.find may crash on
                                -- secret values, so wrap in pcall and fall
                                -- through to raw text if it fails —
                                -- companion sanitizes on its side too.
                                local ok, nulPos = pcall(string.find, text, "\0", 1, true)
                                if ok and nulPos then
                                    text = text:sub(1, nulPos - 1)
                                end
                                wctSeq = wctSeq + 1
                                AddEntry(wctSeq .. "|RAW|" .. text)
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

local function StartPollTimer()
    if pollTicker then return end
    pollTicker = C_Timer.NewTicker(POLL_INTERVAL, PollChatFrames)
    Print("ChatFrame poll every " .. (POLL_INTERVAL * 1000) .. "ms enabled.")
end

local function StopPollTimer()
    if pollTicker then
        pollTicker:Cancel()
        pollTicker = nil
    end
end

-- Enable logging + flush timer + poll (called from both login and /reload)
local function EnableLoggingAndFlush()
    if not ChatTranslatorHelperDB.autoLog then
        Print("Auto-logging disabled. Use /wct log on to enable.")
        return
    end
    if not LoggingChat() then
        LoggingChat(true)
        Print("Chat logging enabled.")
    else
        Print("Chat logging already active.")
    end
    StartFlushTimer()

    -- Initialize memory buffer with markers so the companion app can find it
    -- immediately (before any chat message arrives).
    if not ChatTranslatorHelperDB.wctbuf or ChatTranslatorHelperDB.wctbuf == "" then
        ChatTranslatorHelperDB.wctbuf = "__WCT_BUF__\n__WCT_END__"
        Print("Memory buffer initialized for companion app.")
    end

    -- Start polling ChatFrame scrollback for new messages
    StartPollTimer()
end

-- Init on ADDON_LOADED (fires on both login and /reload)
frame:RegisterEvent("ADDON_LOADED")

frame:SetScript("OnEvent", function(self, event, arg1)
    if event == "ADDON_LOADED" and arg1 == ADDON_NAME then
        if ChatTranslatorHelperDB.autoLog == nil then
            ChatTranslatorHelperDB.autoLog = true
        end
        if ChatTranslatorHelperDB.verbose == nil then
            ChatTranslatorHelperDB.verbose = true
        end
        if ChatTranslatorHelperDB.flushInterval == nil then
            ChatTranslatorHelperDB.flushInterval = 5
        end
        -- Defer to next frame so all systems are ready
        C_Timer.After(0, EnableLoggingAndFlush)
    end
end)

-- Slash command: /wct
SLASH_WCT1 = "/wct"
SlashCmdList["WCT"] = function(msg)
    local cmd = strtrim(msg):lower()

    if cmd == "" or cmd == "status" then
        local logging = LoggingChat()
        Print("Status:")
        Print("  Chat logging: " .. (logging and "|cFF40FF40ON|r" or "|cFFFF4040OFF|r"))
        Print("  Auto-log on login: " .. (ChatTranslatorHelperDB.autoLog and "ON" or "OFF"))
        Print("  Flush timer: " .. (flushTicker and ("|cFF40FF40ON|r (" .. ChatTranslatorHelperDB.flushInterval .. "s)") or "|cFFFF4040OFF|r"))
        Print("  Poll timer: " .. (pollTicker and "|cFF40FF40ON|r" or "|cFFFF4040OFF|r"))
        Print("  Memory buffer: " .. #wctBuf .. "/" .. MSG_LIMIT .. " msgs (seq " .. wctSeq .. ")")
        -- Show tracked frame counts
        local frames = ""
        for i = 1, NUM_CHAT_WINDOWS do
            local cf = _G["ChatFrame" .. i]
            if cf and cf:IsVisible() then
                local c = frameMessageCount[i] or 0
                frames = frames .. " CF" .. i .. "=" .. c
            end
        end
        Print("  Tracked:" .. frames)
        Print("  Use: /wct log|auto|verbose|flush|buf|poll on|off")

    elseif cmd == "log on" then
        LoggingChat(true)
        StartFlushTimer()
        Print("Chat logging |cFF40FF40enabled|r.")

    elseif cmd == "log off" then
        StopFlushTimer()
        LoggingChat(false)
        Print("Chat logging |cFFFF4040disabled|r.")

    elseif cmd == "auto on" then
        ChatTranslatorHelperDB.autoLog = true
        Print("Auto-logging on login |cFF40FF40enabled|r.")

    elseif cmd == "auto off" then
        ChatTranslatorHelperDB.autoLog = false
        Print("Auto-logging on login |cFFFF4040disabled|r.")

    elseif cmd == "verbose on" then
        ChatTranslatorHelperDB.verbose = true
        print("|cFFFFD200[WCT]|r Verbose mode |cFF40FF40enabled|r.")

    elseif cmd == "verbose off" then
        ChatTranslatorHelperDB.verbose = false
        print("|cFFFFD200[WCT]|r Verbose mode |cFFFF4040disabled|r. Only errors will be shown.")

    elseif cmd == "flush on" then
        StartFlushTimer()

    elseif cmd == "flush off" then
        StopFlushTimer()
        Print("Flush timer |cFFFF4040disabled|r.")

    elseif cmd:match("^flush %d+$") then
        local secs = tonumber(cmd:match("^flush (%d+)$"))
        if secs and secs >= 1 and secs <= 60 then
            ChatTranslatorHelperDB.flushInterval = secs
            StopFlushTimer()
            StartFlushTimer()
        else
            Print("Interval must be 1-60 seconds.")
        end

    elseif cmd == "poll on" then
        StartPollTimer()

    elseif cmd == "poll off" then
        StopPollTimer()
        Print("Poll timer |cFFFF4040disabled|r.")

    elseif cmd == "buf" then
        Print("Memory buffer:")
        Print("  Messages: " .. #wctBuf .. "/" .. MSG_LIMIT)
        Print("  Seq: " .. wctSeq)
        local bufLen = ChatTranslatorHelperDB.wctbuf and #ChatTranslatorHelperDB.wctbuf or 0
        Print("  Buffer size: " .. bufLen .. " bytes")

    else
        Print("Unknown command. Use: /wct [status|log|auto|verbose|flush|buf|poll] [on|off|<seconds>]")
    end
end

Print("Scrollback polling active.")
