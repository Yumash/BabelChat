-- ChatTranslatorHelper: auto-enable chat logging for WoWTranslator companion app
-- Minimal addon. All translation logic is in the companion app.

local ADDON_NAME = "ChatTranslatorHelper"
local frame = CreateFrame("Frame")

-- SavedVariables defaults
ChatTranslatorHelperDB = ChatTranslatorHelperDB or {
    autoLog = true,
    verbose = true,
}

local function Print(msg)
    if ChatTranslatorHelperDB.verbose then
        print("|cFFFFD200[WCT]|r " .. msg)
    end
end

-- Auto-enable chat logging on login
frame:RegisterEvent("ADDON_LOADED")
frame:RegisterEvent("PLAYER_LOGIN")

frame:SetScript("OnEvent", function(self, event, arg1)
    if event == "ADDON_LOADED" and arg1 == ADDON_NAME then
        if ChatTranslatorHelperDB.autoLog == nil then
            ChatTranslatorHelperDB.autoLog = true
        end
        if ChatTranslatorHelperDB.verbose == nil then
            ChatTranslatorHelperDB.verbose = true
        end

    elseif event == "PLAYER_LOGIN" then
        if ChatTranslatorHelperDB.autoLog then
            if not LoggingChat() then
                LoggingChat(true)
                Print("Chat logging enabled.")
            else
                Print("Chat logging already active.")
            end
            -- Also enable combat logging to increase disk write frequency
            if not LoggingCombat() then
                LoggingCombat(true)
            end
        else
            Print("Auto-logging disabled. Use /wct log on to enable.")
        end
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
        Print("  Use: /wct log on|off, /wct auto on|off, /wct verbose on|off")

    elseif cmd == "log on" then
        LoggingChat(true)
        Print("Chat logging |cFF40FF40enabled|r.")

    elseif cmd == "log off" then
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

    else
        Print("Unknown command. Use: /wct [status|log on|log off|auto on|auto off|verbose on|verbose off]")
    end
end
