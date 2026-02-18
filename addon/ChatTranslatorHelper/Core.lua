-- ChatTranslatorHelper: auto-enable chat logging for WoWTranslator companion app
-- Minimal addon. All translation logic is in the companion app.

local ADDON_NAME = "ChatTranslatorHelper"
local frame = CreateFrame("Frame")

-- SavedVariables defaults
ChatTranslatorHelperDB = ChatTranslatorHelperDB or {
    autoLog = true,
    verbose = true,
    flushInterval = 5,  -- seconds between LoggingChat toggle flushes
}

-- Flush timer handle
local flushTicker = nil

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

-- Enable logging + flush timer (called from both login and /reload)
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
        Print("  Memory buffer: " .. #wctBuf .. "/" .. MSG_LIMIT .. " msgs (seq " .. wctSeq .. ")")
        Print("  Use: /wct log|auto|verbose|flush|buf on|off, /wct flush <seconds>")

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

    elseif cmd == "buf" then
        Print("Memory buffer:")
        Print("  Messages: " .. #wctBuf .. "/" .. MSG_LIMIT)
        Print("  Seq: " .. wctSeq)
        local bufLen = ChatTranslatorHelperDB.wctbuf and #ChatTranslatorHelperDB.wctbuf or 0
        Print("  Buffer size: " .. bufLen .. " bytes")

    else
        Print("Unknown command. Use: /wct [status|log|auto|verbose|flush|buf] [on|off|<seconds>]")
    end
end

-- ── Memory Buffer for Companion App ──────────────────────────
-- The companion app reads this string from WoW's process memory
-- via ReadProcessMemory. The unique markers __WCT_BUF__ and
-- __WCT_END__ allow the companion to locate the buffer.
--
-- Format: __WCT_BUF__<lines>__WCT_END__
-- Each line: SEQ|CHANNEL|Author-Server|MessageText

local MSG_LIMIT = 50  -- ring buffer size
local wctBuf = {}      -- accumulator table
local wctSeq = 0       -- monotonic sequence counter

-- Chat events to capture
local CHAT_EVENTS = {
    "CHAT_MSG_SAY",
    "CHAT_MSG_YELL",
    "CHAT_MSG_PARTY",
    "CHAT_MSG_PARTY_LEADER",
    "CHAT_MSG_RAID",
    "CHAT_MSG_RAID_LEADER",
    "CHAT_MSG_RAID_WARNING",
    "CHAT_MSG_GUILD",
    "CHAT_MSG_OFFICER",
    "CHAT_MSG_WHISPER",
    "CHAT_MSG_WHISPER_INFORM",
    "CHAT_MSG_INSTANCE_CHAT",
    "CHAT_MSG_INSTANCE_CHAT_LEADER",
}

local wctFrame = CreateFrame("Frame")
for _, evt in ipairs(CHAT_EVENTS) do
    wctFrame:RegisterEvent(evt)
end

wctFrame:SetScript("OnEvent", function(self, event, msg, author, ...)
    if not msg or not author then return end

    wctSeq = wctSeq + 1
    -- Channel name: strip CHAT_MSG_ prefix
    local channel = event:gsub("^CHAT_MSG_", "")

    local entry = wctSeq .. "|" .. channel .. "|" .. author .. "|" .. msg
    tinsert(wctBuf, entry)

    -- Trim to ring buffer size
    while #wctBuf > MSG_LIMIT do
        tremove(wctBuf, 1)
    end

    -- Rebuild contiguous string with markers for ReadProcessMemory
    ChatTranslatorHelperDB.wctbuf = "__WCT_BUF__" .. table.concat(wctBuf, "\n") .. "\n__WCT_END__"
end)
