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

    -- Initialize memory buffer with markers so the companion app can find it
    -- immediately (before any chat message arrives).
    if not ChatTranslatorHelperDB.wctbuf or ChatTranslatorHelperDB.wctbuf == "" then
        ChatTranslatorHelperDB.wctbuf = "__WCT_BUF__\n__WCT_END__"
        Print("Memory buffer initialized for companion app.")
    end
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
-- Each line: SEQ|RAW|formatted_chat_line
--
-- WoW TWW marks CHAT_MSG_* event args as "secret" (tainted).
-- Even ChatFrame_AddMessageEventFilter receives tainted strings.
-- The ONLY safe path: hook ChatFrame:AddMessage() which receives
-- the final formatted (and fully detainted) display string.
-- The companion app parses channel/author/text from this string
-- (same format as WoWChatLog.txt lines).

local MSG_LIMIT = 50  -- ring buffer size
local wctBuf = {}      -- accumulator table
local wctSeq = 0       -- monotonic sequence counter

-- Strip WoW visual markup but KEEP hyperlink structure for parsing.
-- Removes: colors |cXXXXXXXX / |r, textures |T..|t, atlas |A..|a
-- Keeps: |Hchannel:TYPE|h[Name]|h and |Hplayer:Name|h[Name]|h
-- so the companion app can parse channel/author from hyperlinks.
local function StripMarkup(text)
    if not text then return "" end
    local s = text
    -- Remove |cXXXXXXXX (color start)
    s = s:gsub("|c%x%x%x%x%x%x%x%x", "")
    -- Remove |r (color end)
    s = s:gsub("|r", "")
    -- Remove texture escapes |T...|t
    s = s:gsub("|T.-|t", "")
    -- Remove atlas |A.-|a
    s = s:gsub("|A.-|a", "")
    -- Remove |K (BN name replacement) and |k
    s = s:gsub("|K.-|k", "")
    return strtrim(s)
end

local function RebuildBuffer()
    -- Rebuild contiguous string with markers for ReadProcessMemory
    ChatTranslatorHelperDB.wctbuf = "__WCT_BUF__" .. table.concat(wctBuf, "\n") .. "\n__WCT_END__"
end

-- Hook AddMessage on all chat frames to capture formatted lines.
-- Uses hooksecurefunc so we run AFTER the original, preserving
-- WoW's secure/taint execution path (no "secret string" errors).
local function HookChatFrame(cf)
    if not cf or cf._wctHooked then return end
    if not cf.AddMessage then return end

    hooksecurefunc(cf, "AddMessage", function(self, text, r, g, b, ...)
        -- pcall so any error in our code never breaks WoW chat
        pcall(function()
            if not text or text == "" then return end

            -- Strip color codes for clean text
            local clean = StripMarkup(text)
            if not clean or clean == "" then return end

            wctSeq = wctSeq + 1
            local entry = wctSeq .. "|RAW|" .. clean
            tinsert(wctBuf, entry)

            while #wctBuf > MSG_LIMIT do
                tremove(wctBuf, 1)
            end

            RebuildBuffer()
        end)
    end)
    cf._wctHooked = true
end

-- Hook default chat frames (1-10)
for i = 1, 10 do
    local cf = _G["ChatFrame" .. i]
    if cf then
        HookChatFrame(cf)
    end
end
-- Also hook any temporary chat frames created later
hooksecurefunc("FCF_OpenTemporaryWindow", function(...)
    for i = 1, NUM_CHAT_WINDOWS do
        local cf = _G["ChatFrame" .. i]
        if cf and not cf._wctHooked then
            HookChatFrame(cf)
        end
    end
end)

Print("Chat frame hooks active for companion app.")
