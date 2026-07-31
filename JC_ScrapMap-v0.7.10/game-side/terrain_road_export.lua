-- JC ScrapMap road exporter for Scrap Mechanic 1.0 terrain context.
--
-- This file must execute after the active terrain_overworld.lua has defined
-- Generate and Load. It never calls sm.storage.save or sm.terrainData.save.
-- The output path must point to writable mod-owned content data.

local JC_ROAD_MASK = 0x0f00
local JC_ROAD_SHIFT = 8
local JC_TERRAIN_MASK = 0xf000
local JC_TERRAIN_SHIFT = 12
local JC_TERRAIN_DESERT = 3
local JC_TERRAIN_BURNT_FOREST = 5
local JC_TERRAIN_LAKE = 8
local JC_POI_SCHEMATIC_STATION = 141
local JC_OUTPUT_PATH = "$SURVIVAL_DATA/JC_ScrapMap/roads-export.json"
local JC_STATUS_PATH = "$SURVIVAL_DATA/JC_ScrapMap/roads-export-status.json"

g_jcScrapMapRoadExporterHistory = g_jcScrapMapRoadExporterHistory or {}

local function jc_status(stage, message)
    local entry = {
        sequence = #g_jcScrapMapRoadExporterHistory + 1,
        stage = stage,
        message = message
    }
    g_jcScrapMapRoadExporterHistory[#g_jcScrapMapRoadExporterHistory + 1] = entry
    sm.log.info("JC ScrapMap stage: " .. stage .. ": " .. message)
    pcall(sm.json.save, {
        protocol = "jc-scrapmap-export-status-v1",
        stage = stage,
        message = message,
        history = g_jcScrapMapRoadExporterHistory
    }, JC_STATUS_PATH)
end

if g_jcScrapMapRoadExporterInstalled then
    jc_status("already-loaded", "Exporter hooks were already installed; duplicate wrapping was skipped.")
    return
end
g_jcScrapMapRoadExporterInstalled = true

jc_status("loaded", "Exporter Lua loaded and terrain hooks are being installed.")

local function jc_exportRoads()
    if g_cellData == nil or g_cellData.flags == nil or g_cellData.bounds == nil then
        sm.log.warning("JC ScrapMap: generated cell data is unavailable")
        jc_status("waiting", "Generate/Load ran, but generated cell data is unavailable.")
        return
    end

    jc_status("exporting", "Terrain cell data is available; building the export.")

    local roads = {}
    local water = {}
    local desert = {}
    local burntForest = {}
    local schematicStations = {}
    for y = g_cellData.bounds.yMin, g_cellData.bounds.yMax do
        for x = g_cellData.bounds.xMin, g_cellData.bounds.xMax do
            local flags = bit.band(g_cellData.flags[y][x], JC_ROAD_MASK)
            if flags ~= 0 then
                roads[#roads + 1] = { x, y, bit.rshift(flags, JC_ROAD_SHIFT) }
            end
            local terrainType = bit.rshift(bit.band(g_cellData.flags[y][x], JC_TERRAIN_MASK), JC_TERRAIN_SHIFT)
            if terrainType == JC_TERRAIN_LAKE then
                water[#water + 1] = { x, y }
            elseif terrainType == JC_TERRAIN_DESERT then
                desert[#desert + 1] = { x, y }
            elseif terrainType == JC_TERRAIN_BURNT_FOREST then
                burntForest[#burntForest + 1] = { x, y }
            end
            local uid = g_cellData.uid and g_cellData.uid[y] and g_cellData.uid[y][x]
            if uid and GetPoiType(uid) == JC_POI_SCHEMATIC_STATION then
                schematicStations[#schematicStations + 1] = { x, y }
            end
        end
    end

    sm.json.save({
        protocol = "jc-scrapmap-roads-v1",
        seed = g_cellData.seed,
        worldId = g_world and g_world.id or 1,
        bounds = g_cellData.bounds,
        roads = roads,
        water = water,
        desert = desert,
        burntForest = burntForest,
        schematicStations = schematicStations
    }, JC_OUTPUT_PATH)
    sm.log.info(
        "JC ScrapMap: exported " .. tostring(#roads) .. " road cells, " ..
        tostring(#water) .. " water cells, " .. tostring(#desert) ..
        " desert cells, " .. tostring(#burntForest) .. " burnt forest cells, and " ..
        tostring(#schematicStations) .. " schematic stations"
    )
    jc_status("exported", "Road and terrain data was written successfully.")
end

local function jc_exportRoadsSafely()
    local ok, message = pcall(jc_exportRoads)
    if not ok then
        message = tostring(message)
        sm.log.error("JC ScrapMap exporter failed: " .. message)
        jc_status("error", message)
    end
end

local jc_originalGenerate = Generate
function Generate(...)
    jc_status("generate-entered", "The Survival terrain Generate function was entered.")
    local result = jc_originalGenerate(...)
    jc_exportRoadsSafely()
    return result
end

local jc_originalLoad = Load
function Load(...)
    jc_status("load-entered", "The Survival terrain Load function was entered.")
    local result = jc_originalLoad(...)
    if result then
        jc_exportRoadsSafely()
    else
        jc_status("load-returned-false", "The Survival terrain Load function returned without usable saved terrain data.")
    end
    return result
end
