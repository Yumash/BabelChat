-- Config.lua — Settings UI for BabelChat
-- Based on Pirson's WoWTranslator Config, extended with companion settings.

local ADDON_NAME, addonTable = ...
local L = addonTable.L

local function AddTooltip(frame, text)
    if not text then return end
    frame:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetText(text, nil, nil, nil, nil, true)
        GameTooltip:Show()
    end)
    frame:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)
end

function addonTable.CreateConfigUI()
    local db = BabelChatDB
    local panel = CreateFrame("Frame", "ChatTranslatorPanel", UIParent)
    panel.name = "Chat Translator"

    local yOffset = -16

    -- Title
    local title = panel:CreateFontString(nil, "ARTWORK", "GameFontNormalLarge")
    title:SetPoint("TOPLEFT", 16, yOffset)
    title:SetText(L["UI_TITLE"])

    -- Logo
    local logo = panel:CreateTexture(nil, "ARTWORK")
    logo:SetSize(64, 64)
    logo:SetPoint("TOPRIGHT", -20, -10)
    logo:SetTexture("Interface\\Addons\\BabelChat\\img\\logo_wt")

    local version = panel:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
    version:SetPoint("TOP", logo, "BOTTOM", 0, -2)
    version:SetText("v" .. (C_AddOns.GetAddOnMetadata(ADDON_NAME, "Version") or "2.1.0"))

    -- ════════════════════════════════════
    -- SECTION 1: GENERAL
    -- ════════════════════════════════════
    yOffset = yOffset - 40
    local genHeader = panel:CreateFontString(nil, "ARTWORK", "GameFontNormal")
    genHeader:SetPoint("TOPLEFT", 16, yOffset)
    genHeader:SetText("|cffd597ff" .. L["GEN_HEADER"] .. "|r")

    yOffset = yOffset - 25
    local mainCB = CreateFrame("CheckButton", "WCT_MainEnableCB", panel, "InterfaceOptionsCheckButtonTemplate")
    mainCB:SetPoint("TOPLEFT", 16, yOffset)
    _G[mainCB:GetName() .. "Text"]:SetText(L["UI_ENABLE_TEXT"])
    mainCB:SetChecked(db.dict.enabled)
    mainCB:SetScript("OnClick", function(self) db.dict.enabled = self:GetChecked() end)
    AddTooltip(mainCB, L["TT_ENABLE"])

    -- Color button
    local colorBtn = CreateFrame("Button", "WCT_ColorBtn", panel, "UIPanelButtonTemplate")
    colorBtn:SetPoint("LEFT", mainCB, "RIGHT", 220, 0)
    colorBtn:SetSize(120, 22)
    colorBtn:SetText(L["UI_COLOR_BTN"])
    AddTooltip(colorBtn, L["TT_COLOR"])

    local colorPreview = colorBtn:CreateTexture(nil, "OVERLAY")
    colorPreview:SetPoint("LEFT", colorBtn, "RIGHT", 10, 0)
    colorPreview:SetSize(18, 18)

    local function UpdateColorPreview()
        local hex = db.dict.chatColor or "00ff00"
        local r = tonumber(hex:sub(1, 2), 16) / 255
        local g = tonumber(hex:sub(3, 4), 16) / 255
        local b = tonumber(hex:sub(5, 6), 16) / 255
        colorPreview:SetColorTexture(r, g, b)
    end

    colorBtn:SetScript("OnClick", function()
        local hex = db.dict.chatColor or "00ff00"
        ColorPickerFrame:SetupColorPickerAndShow({
            swatchFunc = function()
                local r, g, b = ColorPickerFrame:GetColorRGB()
                db.dict.chatColor = string.format("%02x%02x%02x", r * 255, g * 255, b * 255)
                UpdateColorPreview()
            end,
            hasOpacity = false,
            r = tonumber(hex:sub(1, 2), 16) / 255,
            g = tonumber(hex:sub(3, 4), 16) / 255,
            b = tonumber(hex:sub(5, 6), 16) / 255
        })
    end)
    UpdateColorPreview()

    -- Separator
    yOffset = yOffset - 30
    local line1 = panel:CreateTexture(nil, "ARTWORK")
    line1:SetSize(580, 1)
    line1:SetPoint("TOPLEFT", 16, yOffset)
    line1:SetColorTexture(1, 1, 1, 0.1)

    -- ════════════════════════════════════
    -- SECTION 2: CATEGORIES
    -- ════════════════════════════════════
    yOffset = yOffset - 15
    local filterHeader = panel:CreateFontString(nil, "ARTWORK", "GameFontNormal")
    filterHeader:SetPoint("TOPLEFT", 16, yOffset)
    filterHeader:SetText("|cffd597ff" .. L["CAT_HEADER"] .. "|r")

    local categories = {
        { text = L["CAT_MAZZ"],    key = "showMazz",        tt = L["TT_CAT_MAZZ"] },
        { text = L["CAT_SOCIAL"],  key = "showSocial",      tt = L["TT_CAT_SOCIAL"] },
        { text = L["CAT_CLASSES"], key = "showClases",      tt = L["TT_CAT_CLASSES"] },
        { text = L["CAT_ROLES"],   key = "showRoles",       tt = L["TT_CAT_ROLES"] },
        { text = L["CAT_STATS"],   key = "showStats",       tt = L["TT_CAT_STATS"] },
        { text = L["CAT_PROF"],    key = "showProfesiones", tt = L["TT_CAT_PROF"] },
        { text = L["CAT_COMBAT"],  key = "showCombate",     tt = L["TT_CAT_COMBAT"] },
        { text = L["CAT_TRADE"],   key = "showComercio",    tt = L["TT_CAT_TRADE"] },
        { text = L["CAT_GROUPS"],  key = "showGrupos",      tt = L["TT_CAT_GROUPS"] },
        { text = L["CAT_GUILD"],   key = "showHermandad",   tt = L["TT_CAT_GUILD"] },
        { text = L["CAT_STATUS"],  key = "showEstado",      tt = L["TT_CAT_STATUS"] },
        { text = L["CAT_SLANG"],   key = "showSlang",       tt = L["TT_CAT_SLANG"] },
        { text = L["CAT_ZONES"],   key = "showZones",       tt = L["TT_CAT_ZONES"] },
        { text = L["CAT_SETS"],    key = "showSets",        tt = L["TT_CAT_SETS"] },
    }

    yOffset = yOffset - 5
    for i, info in ipairs(categories) do
        local cb = CreateFrame("CheckButton", "WCT_CB_" .. info.key, panel, "InterfaceOptionsCheckButtonTemplate")
        local col = ((i - 1) % 3)
        local row = math.floor((i - 1) / 3)
        cb:SetPoint("TOPLEFT", 16 + col * 190, yOffset - row * 25)
        _G[cb:GetName() .. "Text"]:SetText(info.text)
        _G[cb:GetName() .. "Text"]:SetFontObject("GameFontHighlightSmall")
        cb:SetChecked(db.dict.settings[info.key])
        cb:SetScript("OnClick", function(self)
            db.dict.settings[info.key] = self:GetChecked()
            addonTable.RebuildMasterDict()
        end)
        AddTooltip(cb, info.tt)
    end

    local catRows = math.ceil(#categories / 3)
    yOffset = yOffset - catRows * 25 - 10

    -- Separator
    local line2 = panel:CreateTexture(nil, "ARTWORK")
    line2:SetSize(580, 1)
    line2:SetPoint("TOPLEFT", 16, yOffset)
    line2:SetColorTexture(1, 1, 1, 0.1)

    -- ════════════════════════════════════
    -- SECTION 3: CHANNELS
    -- ════════════════════════════════════
    yOffset = yOffset - 15
    local channelHeader = panel:CreateFontString(nil, "ARTWORK", "GameFontNormal")
    channelHeader:SetPoint("TOPLEFT", 16, yOffset)
    channelHeader:SetText("|cffd597ff" .. L["CH_HEADER"] .. "|r")

    local channelSettings = {
        { text = L["CH_SAY"],     events = { "CHAT_MSG_SAY", "CHAT_MSG_YELL" },                                                                      tt = L["TT_CH_SAY"] },
        { text = L["CH_PARTY"],   events = { "CHAT_MSG_PARTY", "CHAT_MSG_PARTY_LEADER", "CHAT_MSG_INSTANCE_CHAT", "CHAT_MSG_INSTANCE_CHAT_LEADER" }, tt = L["TT_CH_PARTY"] },
        { text = L["CH_RAID"],    events = { "CHAT_MSG_RAID", "CHAT_MSG_RAID_LEADER", "CHAT_MSG_RAID_WARNING" },                                     tt = L["TT_CH_RAID"] },
        { text = L["CH_GUILD"],   events = { "CHAT_MSG_GUILD", "CHAT_MSG_OFFICER" },                                                                 tt = L["TT_CH_GUILD"] },
        { text = L["CH_WHISPER"], events = { "CHAT_MSG_WHISPER", "CHAT_MSG_WHISPER_INFORM", "CHAT_MSG_BN_WHISPER" },                                 tt = L["TT_CH_WHISPER"] },
        { text = L["CH_CHANNEL"], events = { "CHAT_MSG_CHANNEL" },                                                                                   tt = L["TT_CH_CHANNEL"] },
        { text = L["CH_EMOTE"],   events = { "CHAT_MSG_EMOTE" },                                                                                     tt = L["TT_CH_EMOTE"] },
    }

    yOffset = yOffset - 5
    for i, info in ipairs(channelSettings) do
        local cb = CreateFrame("CheckButton", "WCT_CH_CB_" .. i, panel, "InterfaceOptionsCheckButtonTemplate")
        local col = ((i - 1) % 3)
        local row = math.floor((i - 1) / 3)
        cb:SetPoint("TOPLEFT", 16 + col * 190, yOffset - row * 25)
        _G[cb:GetName() .. "Text"]:SetText(info.text)
        _G[cb:GetName() .. "Text"]:SetFontObject("GameFontHighlightSmall")

        local isEnabled = true
        for _, ev in ipairs(info.events) do
            if db.dict.settings.channels[ev] == false then
                isEnabled = false
                break
            end
        end
        cb:SetChecked(isEnabled)

        cb:SetScript("OnClick", function(self)
            local val = self:GetChecked()
            for _, ev in ipairs(info.events) do
                db.dict.settings.channels[ev] = val
            end
        end)
        AddTooltip(cb, info.tt)
    end

    local chRows = math.ceil(#channelSettings / 3)
    yOffset = yOffset - chRows * 25 - 10

    -- Separator
    local line3 = panel:CreateTexture(nil, "ARTWORK")
    line3:SetSize(580, 1)
    line3:SetPoint("TOPLEFT", 16, yOffset)
    line3:SetColorTexture(1, 1, 1, 0.1)

    -- ════════════════════════════════════
    -- SECTION 4: LANGUAGE SELECTOR
    -- ════════════════════════════════════
    yOffset = yOffset - 15
    local langLabel = panel:CreateFontString(nil, "ARTWORK", "GameFontHighlight")
    langLabel:SetPoint("TOPLEFT", 16, yOffset)
    langLabel:SetText("|cffd597ff" .. L["UI_LANG_LABEL"] .. "|r")

    local langNames = {
        enUS = "English",
        esES = "Español (ES)",
        esMX = "Español (AL)",
        deDE = "Deutsch",
        frFR = "Français",
        itIT = "Italiano",
        ptBR = "Português",
        ruRU = "Русский",
        koKR = "한국어",
        zhCN = "简体中文",
        zhTW = "繁體中文",
        plPL = "Polski",
        svSE = "Svenska",
        noNO = "Norsk"
    }

    local dropdown = CreateFrame("Frame", "WCT_LangDrop", panel, "UIDropDownMenuTemplate")
    dropdown:SetPoint("TOPLEFT", langLabel, "BOTTOMLEFT", -15, -5)
    AddTooltip(dropdown, L["TT_LANG"])

    UIDropDownMenu_Initialize(dropdown, function()
        for val, name in pairs(langNames) do
            local info = UIDropDownMenu_CreateInfo()
            info.text = name
            info.value = val
            info.func = function(s)
                db.dict.targetLocale = s.value
                UIDropDownMenu_SetSelectedValue(dropdown, s.value)
                UIDropDownMenu_SetText(dropdown, langNames[s.value])
                addonTable.RebuildMasterDict()
            end
            info.checked = (db.dict.targetLocale == val)
            UIDropDownMenu_AddButton(info)
        end
    end)

    UIDropDownMenu_SetSelectedValue(dropdown, db.dict.targetLocale)
    UIDropDownMenu_SetText(dropdown, langNames[db.dict.targetLocale] or "English")

    -- Test button
    local testBtn = CreateFrame("Button", "WCT_TestBtn", panel, "UIPanelButtonTemplate")
    testBtn:SetPoint("LEFT", dropdown, "RIGHT", 140, 2)
    testBtn:SetSize(150, 22)
    testBtn:SetText(L["UI_TEST_BTN"])
    testBtn:SetScript("OnClick", function() addonTable.RunTest() end)
    AddTooltip(testBtn, L["TT_TEST_BTN"])

    yOffset = yOffset - 60

    -- Separator
    local line4 = panel:CreateTexture(nil, "ARTWORK")
    line4:SetSize(580, 1)
    line4:SetPoint("TOPLEFT", 16, yOffset)
    line4:SetColorTexture(1, 1, 1, 0.1)

    -- ════════════════════════════════════
    -- SECTION 5: COMPANION APP
    -- ════════════════════════════════════
    yOffset = yOffset - 15
    local compHeader = panel:CreateFontString(nil, "ARTWORK", "GameFontNormal")
    compHeader:SetPoint("TOPLEFT", 16, yOffset)
    compHeader:SetText("|cffd597ff" .. L["COMP_HEADER"] .. "|r")

    yOffset = yOffset - 25
    local compCB = CreateFrame("CheckButton", "WCT_CompEnableCB", panel, "InterfaceOptionsCheckButtonTemplate")
    compCB:SetPoint("TOPLEFT", 16, yOffset)
    _G[compCB:GetName() .. "Text"]:SetText(L["COMP_ENABLE"])
    compCB:SetChecked(db.companion.enabled)
    compCB:SetScript("OnClick", function(self)
        db.companion.enabled = self:GetChecked()
        if db.companion.enabled then
            addonTable.StartBufferFlush()
        else
            addonTable.StopBufferFlush()
        end
    end)
    AddTooltip(compCB, L["TT_COMP_ENABLE"])

    -- ════════════════════════════════════
    -- REGISTER PANEL
    -- ════════════════════════════════════
    local config_category = Settings.RegisterCanvasLayoutCategory(panel, panel.name)
    Settings.RegisterAddOnCategory(config_category)
    addonTable.categoryID = config_category:GetID()
end
