-- Core.lua — BabelChat v2.2.2
-- Thin init: wires DictEngine + CompanionBuffer + ChatFilter + slash commands.
-- Dictionary translation inline in chat + memory buffer for companion overlay.

local ADDON_NAME, addonTable = ...
local L = addonTable.L

local PREFIX = "|cffffff00[|r|cffd597ffChat Translator|r|cffffff00]|r "

local function Print(msg)
    print(PREFIX .. msg)
end

-- ==========================================
-- DEFAULT DATABASE
-- ==========================================
local DEFAULTS = {
    -- Dictionary settings (from Pirson's WoWTranslator)
    dict = {
        enabled = true,
        targetLocale = "esES",
        chatColor = "00ff00",
        settings = {
            showMazz = true,
            showSocial = true,
            showClases = true,
            showCombate = true,
            showComercio = true,
            showStats = true,
            showGrupos = true,
            showHermandad = true,
            showProfesiones = true,
            showRoles = true,
            showEstado = true,
            showSlang = true,
            showZones = true,
            showSets = true,
            skipSameLanguage = true,
            channels = {}
        }
    },
    -- Companion app settings (disabled by default — addon works standalone)
    companion = {
        enabled = false,
        autoLog = false,
        verbose = false,
        flushInterval = 5,
        pollFallback = false,
    },
    -- First run flag
    firstRun = true,
    -- Minimap icon
    minimap = {},
}

-- Deep merge defaults into db (non-destructive)
local function ApplyDefaults(db, defaults)
    for k, v in pairs(defaults) do
        if type(v) == "table" then
            if db[k] == nil then db[k] = {} end
            if type(db[k]) == "table" then
                ApplyDefaults(db[k], v)
            end
        elseif db[k] == nil then
            db[k] = v
        end
    end
end

-- Auto-detect target locale from WoW client locale
local function AutoDetectLocale()
    local db = BabelChatDB
    local clientLocale = GetLocale()
    -- If target locale is still default and client is not EN, set to client locale
    if db.dict.targetLocale == "enUS" and clientLocale ~= "enUS" and clientLocale ~= "enGB" then
        db.dict.targetLocale = clientLocale
    end
end

-- ==========================================
-- CHAT EVENT FILTER (dual-path)
-- ==========================================
local CHAT_EVENTS = {
    "CHAT_MSG_SAY", "CHAT_MSG_YELL",
    "CHAT_MSG_WHISPER", "CHAT_MSG_WHISPER_INFORM",
    "CHAT_MSG_BN_WHISPER",
    "CHAT_MSG_PARTY", "CHAT_MSG_PARTY_LEADER",
    "CHAT_MSG_RAID", "CHAT_MSG_RAID_LEADER", "CHAT_MSG_RAID_WARNING",
    "CHAT_MSG_INSTANCE_CHAT", "CHAT_MSG_INSTANCE_CHAT_LEADER",
    "CHAT_MSG_GUILD", "CHAT_MSG_OFFICER",
    "CHAT_MSG_CHANNEL", "CHAT_MSG_EMOTE",
    "CHAT_MSG_BATTLEGROUND", "CHAT_MSG_BATTLEGROUND_LEADER",
}

local function ChatFilter(self, event, text, author, ...)
    local db = BabelChatDB
    if not db then return end

    -- Strip CHAT_MSG_ prefix for compact event name
    local shortEvent = event:gsub("^CHAT_MSG_", "")

    -- Dictionary translation (if enabled and channel not filtered)
    local translated, wasChanged
    local dictChannelEnabled = not db.dict.settings.channels or db.dict.settings.channels[event] ~= false
    if db.dict.enabled and dictChannelEnabled then
        -- pcall for safety (secret values in instance chat)
        local ok, t, c = pcall(addonTable.TranslateChat, text)
        if ok then
            translated, wasChanged = t, c
        end
    end

    -- Buffer for companion app — ALL channels, regardless of dict filter
    if wasChanged then
        addonTable.BufferAddEntry(text, "DICT", shortEvent, author, translated)
    else
        addonTable.BufferAddEntry(text, "RAW", shortEvent, author)
    end

    -- Return modified text for inline chat display
    if wasChanged then
        return false, translated, author, ...
    end
end

-- ==========================================
-- SLASH COMMANDS: /babel
-- ==========================================
SLASH_BABELCHAT1 = "/babel"
SlashCmdList["BABELCHAT"] = function(msg)
    local command = strtrim(msg):lower()
    local db = BabelChatDB

    if command == "config" or command == "settings" then
        if Settings and Settings.OpenToCategory and addonTable.categoryID then
            Settings.OpenToCategory(addonTable.categoryID)
        else
            Print("Settings panel not available. Use the game's AddOn settings.")
        end

    elseif command == "on" then
        db.dict.enabled = true
        Print(L["SLASH_ON"])

    elseif command == "off" then
        db.dict.enabled = false
        Print(L["SLASH_OFF"])

    elseif command == "test" then
        addonTable.RunTest()

    elseif command == "companion" or command == "buf" then
        local count, seq, limit, flushing = addonTable.GetBufferStatus()
        Print("Companion buffer:")
        Print("  Messages: " .. count .. "/" .. limit)
        Print("  Seq: " .. seq)
        Print("  Flush: " .. (flushing and "|cFF40FF40ON|r" or "|cFFFF4040OFF|r"))
        Print("  Poll fallback: " .. (addonTable.IsPollActive() and "|cFF40FF40ON|r" or "|cFFFF4040OFF|r"))

    elseif command == "poll on" then
        addonTable.StartPollTimer()
        Print("Poll fallback |cFF40FF40enabled|r.")

    elseif command == "poll off" then
        addonTable.StopPollTimer()
        Print("Poll fallback |cFFFF4040disabled|r.")

    elseif command == "log on" then
        if not LoggingChat() then LoggingChat(true) end
        addonTable.StartLogFlush(db.companion.flushInterval)
        Print("Chat logging |cFF40FF40enabled|r.")

    elseif command == "log off" then
        addonTable.StopLogFlush()
        if LoggingChat() then LoggingChat(false) end
        Print("Chat logging |cFFFF4040disabled|r.")

    else
        Print("|cffd597ff" .. L["HELP_HEADER"] .. "|r")
        Print("|cffffff00/babel config|r - " .. L["HELP_CONFIG_MSG"])
        Print("|cffffff00/babel on|off|r - " .. L["HELP_ONOFF_MSG"])
        Print("|cffffff00/babel test|r - " .. L["HELP_TEST_MSG"])
        Print("|cffffff00/babel companion|r - " .. L["HELP_COMPANION_MSG"])
        Print("|cffffff00/babel poll on|off|r - Toggle GetMessageInfo fallback")
        Print("|cffffff00/babel log on|off|r - Toggle chat file logging")
    end
end

-- ==========================================
-- TEST FUNCTION
-- ==========================================
function addonTable.RunTest()
    local testMsg = "LFM ICC HC 25m Need Tank and Healer"
    local translated, changed = addonTable.TranslateChat(testMsg)

    Print("|cffffff00" .. L["SLASH_TEST_ORIGINAL"] .. "|cffffffff" .. testMsg .. "|r")
    if changed then
        Print("|cffffff00" .. L["SLASH_TEST_RESULT"] .. "|cffffffff" .. translated .. "|r")
    else
        local db = BabelChatDB
        local errorStr = (not db.dict.enabled) and L["SLASH_TEST_ERROR"] or L["TEST_NO_MATCH"]
        Print("|cffff0000" .. errorStr .. "|r")
    end
end

-- ==========================================
-- WELCOME FRAME (first run popup)
-- ==========================================
function addonTable.ShowWelcomeFrame()
    if addonTable.welcomeFrame then
        addonTable.welcomeFrame:Show()
        return
    end

    local frame = CreateFrame("Frame", "BabelChatWelcomeFrame", UIParent, "BasicFrameTemplateWithInset")
    frame:SetSize(420, 320)
    frame:SetPoint("CENTER")
    frame:SetMovable(true)
    frame:EnableMouse(true)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
    frame:SetFrameStrata("DIALOG")
    frame.TitleBg:SetHeight(30)

    -- Title
    frame.title = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightLarge")
    frame.title:SetPoint("TOP", frame.TitleBg, "TOP", 0, -3)
    frame.title:SetText("BabelChat")

    -- Body text
    local body = frame.InsetBg or frame.Inset
    local text = frame:CreateFontString(nil, "ARTWORK", "GameFontNormal")
    text:SetPoint("TOPLEFT", frame, "TOPLEFT", 18, -60)
    text:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -18, -60)
    text:SetJustifyH("LEFT")
    text:SetSpacing(4)

    -- Strip color codes for clean display, re-apply manually
    local lines = {
        L["WELCOME_1"],
        "",
        L["WELCOME_2"],
        "",
        L["WELCOME_3"],
        "",
        L["WELCOME_4"],
        L["WELCOME_5"],
        L["WELCOME_6"],
    }
    text:SetText(table.concat(lines, "\n"))

    -- Settings button
    local settingsBtn = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    settingsBtn:SetSize(120, 26)
    settingsBtn:SetPoint("BOTTOMRIGHT", frame, "BOTTOM", -4, 14)
    settingsBtn:SetText(L["WELCOME_SETTINGS"])
    settingsBtn:SetScript("OnClick", function()
        frame:Hide()
        if Settings and Settings.OpenToCategory and addonTable.categoryID then
            Settings.OpenToCategory(addonTable.categoryID)
        end
    end)

    -- OK button
    local okBtn = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    okBtn:SetSize(120, 26)
    okBtn:SetPoint("BOTTOMLEFT", frame, "BOTTOM", 4, 14)
    okBtn:SetText(L["WELCOME_OK"])
    okBtn:SetScript("OnClick", function()
        frame:Hide()
    end)

    addonTable.welcomeFrame = frame
    frame:Show()
end

-- ==========================================
-- INITIALIZATION
-- ==========================================
local initFrame = CreateFrame("Frame")
initFrame:RegisterEvent("PLAYER_LOGIN")

initFrame:SetScript("OnEvent", function(self, event)
    -- Migrate from old ChatTranslatorHelper if present
    if ChatTranslatorHelperDB and not BabelChatDB then
        BabelChatDB = ChatTranslatorHelperDB
        Print("|cFF40FF40Migrated settings from ChatTranslatorHelper.|r")
    end

    -- Initialize database
    if not BabelChatDB then
        BabelChatDB = {}
    end
    ApplyDefaults(BabelChatDB, DEFAULTS)

    local db = BabelChatDB

    -- Initialize default channel states
    for _, e in ipairs(CHAT_EVENTS) do
        if db.dict.settings.channels[e] == nil then
            db.dict.settings.channels[e] = true
        end
    end

    -- Auto-detect locale
    AutoDetectLocale()

    -- Pre-allocate companion keys (pointer stability)
    addonTable.PreallocateCompanionKeys()

    -- Initialize LibBabble
    addonTable.InitLibBabble()

    -- Build master dictionary
    addonTable.RebuildMasterDict()

    -- Register chat event filter for all channels
    for _, e in ipairs(CHAT_EVENTS) do
        ChatFrame_AddMessageEventFilter(e, ChatFilter)
    end

    -- Start companion buffer flush
    if db.companion.enabled then
        addonTable.StartBufferFlush()
    end

    -- Start chat log flush if auto-logging enabled
    if db.companion.autoLog then
        if not LoggingChat() then LoggingChat(true) end
        addonTable.StartLogFlush(db.companion.flushInterval)
    end

    -- Start poll fallback if explicitly enabled
    if db.companion.pollFallback then
        addonTable.StartPollTimer()
    end

    -- Create config UI
    addonTable.CreateConfigUI()

    -- Minimap button
    local LDB = LibStub("LibDataBroker-1.1", true)
    local LDBIcon = LibStub("LibDBIcon-1.0", true)
    if LDB and LDBIcon then
        local dataObject = LDB:NewDataObject("BabelChat", {
            type = "launcher",
            icon = "Interface\\Addons\\BabelChat\\img\\logo_wt",
            OnClick = function()
                if Settings and Settings.OpenToCategory and addonTable.categoryID then
                    Settings.OpenToCategory(addonTable.categoryID)
                end
            end,
            OnTooltipShow = function(tooltip)
                tooltip:AddLine(L["QT_MINIMAP_TT"] or "Click: Open Settings")
            end,
        })
        if not LDBIcon:IsRegistered("BabelChat") then
            LDBIcon:Register("BabelChat", dataObject, db.minimap)
        end
    end

    -- First run: show welcome popup
    if db.firstRun then
        db.firstRun = false
        C_Timer.After(3, function()
            addonTable.ShowWelcomeFrame()
        end)
    else
        Print(L["CHAT_LOADED"])
    end
end)
