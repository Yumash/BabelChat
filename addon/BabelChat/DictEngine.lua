-- DictEngine.lua — Dictionary-based translation engine
-- Based on WoW Translator by Pirson (CurseForge project 1431567)
-- Adapted for BabelChat merged addon

local ADDON_NAME, addonTable = ...

-- ==========================================
-- MASTER DICTIONARY & LOOKUP TABLES
-- ==========================================
local MasterDict = {}
local MultiWordPatterns = {}
local SortedDictKeys = {}

local ipairs, pairs = ipairs, pairs
local string_format, string_gsub, string_find, string_lower = string.format, string.gsub, string.find, string.lower
local table_insert, table_sort = table.insert, table.sort

-- LibBabble references (set on init)
local BZ, BI

function addonTable.InitLibBabble()
    BZ = LibStub("LibBabble-SubZone-3.0", true) and LibStub("LibBabble-SubZone-3.0"):GetUnstrictLookupTable()
    BI = LibStub("LibBabble-ItemSet-3.0", true) and LibStub("LibBabble-ItemSet-3.0"):GetUnstrictLookupTable()
end

-- ==========================================
-- BUILD MASTER DICTIONARY FROM DATA FILES
-- ==========================================
function addonTable.RebuildMasterDict()
    MasterDict = {}
    MultiWordPatterns = {}
    SortedDictKeys = {}

    local db = BabelChatDB
    if not db or not db.dict then return end

    local map = {
        { key = "showMazz",        dict = addonTable.MazzRaidDict },
        { key = "showSocial",      dict = addonTable.SocialDict },
        { key = "showClases",      dict = addonTable.ClasesDict },
        { key = "showCombate",     dict = addonTable.CombateDict },
        { key = "showComercio",    dict = addonTable.ComercioDict },
        { key = "showStats",       dict = addonTable.EstadisticasDict },
        { key = "showGrupos",      dict = addonTable.GruposDict },
        { key = "showHermandad",   dict = addonTable.HermandadDict },
        { key = "showProfesiones", dict = addonTable.ProfesionesDict },
        { key = "showRoles",       dict = addonTable.RolesDict },
        { key = "showEstado",      dict = addonTable.EstadoDict },
        { key = "showSlang",       dict = addonTable.SlangDict },
    }

    local target = db.dict.targetLocale or "enUS"

    for _, entry in ipairs(map) do
        if entry.dict and db.dict.settings[entry.key] then
            for k, v in pairs(entry.dict) do
                local lowerK = string_lower(k)
                local translation = v[target] or v["enUS"] or k

                if string_find(k, " ") then
                    if not MultiWordPatterns[lowerK] then
                        MultiWordPatterns[lowerK] = translation
                        table_insert(SortedDictKeys, lowerK)
                    end
                else
                    MasterDict[lowerK] = translation
                end
            end
        end
    end

    table_sort(SortedDictKeys, function(a, b) return #a > #b end)
end

-- ==========================================
-- TRANSLATION ENGINE
-- ==========================================
-- Collects translations as a clean annotation line below the original,
-- instead of injecting color codes inline (which pollutes chat readability).
-- Output: "original text" unchanged, plus annotation "→ term1, term2, ..."

-- Find all hyperlink ranges in text (|H...|h...|h and |cff...|r blocks)
-- Returns list of {start, end} pairs that should be excluded from matching
local function FindHyperlinkRanges(text)
    local ranges = {}
    -- Match |H...|h...|h hyperlinks
    local searchStart = 1
    while searchStart <= #text do
        local hStart = string_find(text, "|H", searchStart, true)
        if not hStart then break end
        -- Find closing |h (second one after |h[text]|h)
        local firstH = string_find(text, "|h", hStart + 2, true)
        if firstH then
            local secondH = string_find(text, "|h", firstH + 2, true)
            local hEnd = secondH and (secondH + 1) or (firstH + 1)
            table_insert(ranges, { hStart, hEnd })
            searchStart = hEnd + 1
        else
            break
        end
    end
    -- Match |cff......|r color code blocks
    searchStart = 1
    while searchStart <= #text do
        local cStart = string_find(text, "|c", searchStart, true)
        if not cStart then break end
        local rEnd = string_find(text, "|r", cStart + 10, true)
        if rEnd then
            table_insert(ranges, { cStart, rEnd + 1 })
            searchStart = rEnd + 2
        else
            break
        end
    end
    return ranges
end

-- Check if a position range is inside any hyperlink/color block
local function IsInsideHyperlink(startPos, endPos, linkRanges)
    for _, r in ipairs(linkRanges) do
        if startPos >= r[1] and endPos <= r[2] then
            return true
        end
    end
    return false
end

function addonTable.TranslateChat(text)
    local db = BabelChatDB
    if not text or not db or not db.dict or not db.dict.enabled then return text, false end

    local translations = {}  -- { "original → translation", ... }
    local matched = {}       -- track matched ranges to prevent overlaps
    local textLower = string_lower(text)
    local userColor = db.dict.chatColor or "00ff00"
    local linkRanges = FindHyperlinkRanges(text)

    -- 1. Multi-word phrase translation (longest first, no overlaps, skip hyperlinks)
    for _, eng in ipairs(SortedDictKeys) do
        local startPos = string_find(textLower, eng, 1, true)
        if startPos then
            local endPos = startPos + #eng - 1
            -- Skip if inside a hyperlink or color code block
            if not IsInsideHyperlink(startPos, endPos, linkRanges) then
                local overlaps = false
                for _, r in ipairs(matched) do
                    if startPos <= r[2] and endPos >= r[1] then
                        overlaps = true
                        break
                    end
                end
                if not overlaps then
                    table_insert(matched, { startPos, endPos })
                    table_insert(translations, eng .. " → " .. MultiWordPatterns[eng])
                end
            end
        end
    end

    -- 2. Single-word translation (skip hyperlinks and already-matched ranges)
    for word in text:gmatch("([%a%d']+)") do
        local translation = MasterDict[string_lower(word)]
        if translation then
            local startPos = string_find(textLower, string_lower(word), 1, true)
            local overlaps = false
            if startPos then
                local endPos = startPos + #word - 1
                -- Skip if inside hyperlink
                if IsInsideHyperlink(startPos, endPos, linkRanges) then
                    overlaps = true
                else
                    for _, r in ipairs(matched) do
                        if startPos <= r[2] and endPos >= r[1] then
                            overlaps = true
                            break
                        end
                    end
                    if not overlaps then
                        table_insert(matched, { startPos, endPos })
                    end
                end
            end
            if not overlaps then
                table_insert(translations, word .. " → " .. translation)
            end
        end
    end

    -- 3. LibBabble zone & item set translations
    local babbleData = {
        { data = BZ, active = db.dict.settings.showZones },
        { data = BI, active = db.dict.settings.showSets }
    }
    for _, b in ipairs(babbleData) do
        if b.data and b.active then
            for eng, loc in pairs(b.data) do
                if #eng > 3 then
                    local bStart = string_find(textLower, string_lower(eng), 1, true)
                    if bStart and not IsInsideHyperlink(bStart, bStart + #eng - 1, linkRanges) then
                        table_insert(translations, eng .. " → " .. loc)
                    end
                end
            end
        end
    end

    if #translations == 0 then
        return text, false
    end

    -- Build clean annotation line below the original
    local annotation = "|cff" .. userColor .. "   → " .. table.concat(translations, ", ") .. "|r"
    return text .. "\n" .. annotation, true
end
