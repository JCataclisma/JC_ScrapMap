-- Packaged copy. Keep synchronized with game-side/terrain_road_export.lua.

local JC_ROAD_MASK = 0x0f00
local JC_ROAD_SHIFT = 8
local JC_TERRAIN_MASK = 0xf000
local JC_TERRAIN_SHIFT = 12
local JC_TERRAIN_LAKE = 8
local JC_OUTPUT_PATH = "$CONTENT_8f3672f0-1d70-4a65-a47b-fd411c8cbf60/roads-export.json"

local function jc_exportRoads()
    if g_cellData == nil or g_cellData.flags == nil or g_cellData.bounds == nil then
        sm.log.warning("JC ScrapMap: generated cell data is unavailable")
        return
    end

    local roads = {}
    local water = {}
    for y = g_cellData.bounds.yMin, g_cellData.bounds.yMax do
        for x = g_cellData.bounds.xMin, g_cellData.bounds.xMax do
            local flags = bit.band(g_cellData.flags[y][x], JC_ROAD_MASK)
            if flags ~= 0 then
                roads[#roads + 1] = { x, y, bit.rshift(flags, JC_ROAD_SHIFT) }
            end
            local terrainType = bit.rshift(bit.band(g_cellData.flags[y][x], JC_TERRAIN_MASK), JC_TERRAIN_SHIFT)
            if terrainType == JC_TERRAIN_LAKE then
                water[#water + 1] = { x, y }
            end
        end
    end

    sm.json.save({
        protocol = "jc-scrapmap-roads-v1",
        seed = g_cellData.seed,
        worldId = g_world and g_world.id or 1,
        bounds = g_cellData.bounds,
        roads = roads,
        water = water
    }, JC_OUTPUT_PATH)
    sm.log.info("JC ScrapMap: exported " .. tostring(#roads) .. " road cells and " .. tostring(#water) .. " water cells")
end

local jc_originalGenerate = Generate
function Generate(...)
    local result = jc_originalGenerate(...)
    jc_exportRoads()
    return result
end

local jc_originalLoad = Load
function Load(...)
    local result = jc_originalLoad(...)
    if result then
        jc_exportRoads()
    end
    return result
end
