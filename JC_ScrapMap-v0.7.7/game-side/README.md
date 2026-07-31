# Launcher-managed exact-road helper

These files implement the opt-in exact-road helper used by
`road-helper.ps1`.

Players must not install or activate them manually. Choose **Generate exact
roads** from `Start JC ScrapMap.cmd`. The launcher temporarily copies the
exporter beside the built-in Survival terrain scripts, applies one marked
terrain-script hook, launches the game, captures the result, and
removes/restores everything after the game closes. It does not depend on a
copied local mod being registered under a player profile.

The helper reads generated `g_cellData.flags`, scans once per overworld load,
and writes only directional road records. It does not call `sm.storage.save`,
`sm.terrainData.save`, or any save-mutation API.
