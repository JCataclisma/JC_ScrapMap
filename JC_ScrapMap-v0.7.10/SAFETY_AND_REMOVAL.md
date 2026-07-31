# Safety and Complete Removal

## Ordinary Open Map

`Open map` does not install a mod, patch Steam files, or write to a Scrap
Mechanic save. It reads the selected SQLite save with read-only and query-only
settings, hashes it before and after inspection, and writes mapper-owned files
only inside the JC ScrapMap folder.

## Exact Terrain Generation

Option 2 is explicit and temporary. It may affect only:

- `<Steam>\steamapps\common\Scrap Mechanic\Survival\Scripts\terrain\terrain_overworld.lua`
- `<Steam>\steamapps\common\Scrap Mechanic\Survival\Scripts\terrain\jc_scrapmap_road_export.lua`
- `<Steam>\steamapps\common\Scrap Mechanic\Survival\JC_ScrapMap`
- `<JC ScrapMap>\.road-helper`
- `<JC ScrapMap>\imports\roads-<seed>.json`

The installed terrain script receives one delimited JC ScrapMap hook. Its
original bytes and SHA-256 hash are recorded first. Cleanup restores the
original and verifies that hash. If the installed file changed unexpectedly,
the launcher refuses to overwrite it.

The helper does not call Scrap Mechanic save-storage APIs.

## Interrupted Recovery

If Scrap Mechanic exits or crashes before capture, the separate generation
window detects it and attempts verified automatic cleanup. If Windows, Steam,
the helper window, or the computer interrupts option 2 and recovery state
remains:

1. Do not delete `.road-helper`.
2. Close Scrap Mechanic.
3. Start JC ScrapMap.
4. Choose `3. Disable/repair road helper`.
5. Choose option 4 and confirm the status is `disabled`.

If repair reports that the installed script changed unexpectedly, preserve the
whole JC ScrapMap folder and review the reported paths before changing
anything manually.

## Files JC ScrapMap Creates

Inside its own folder:

- `.road-helper\state.json`
- `.road-helper\terrain_overworld.original.lua`
- `.road-helper\last-generation.json`
- `JC_ScrapMap_Diagnostic_<timestamp>_<run-id>.txt`
- `generated\state.json`
- `imports\roads-<seed>.json`
- `mapper-data\<save-identity>\state.json`
- `mapper-data\<save-identity>\markers.json`
- `mapper-data\<save-identity>\discoveries.json`

During option 2 only:

- the temporary `jc_scrapmap_road_export.lua` Survival exporter;
- the ownership-marked temporary `Survival\JC_ScrapMap` output directory;
- one marked hook in the installed `terrain_overworld.lua`.

JC ScrapMap does not create Steam Workshop items, online accounts, registry
entries, services, scheduled tasks, or startup entries.

The private runtime stays under `<JC ScrapMap>\runtime\python`. It does not add
Python to `PATH`, register file associations, install packages, or modify a
system Python installation.

## Complete Removal

1. Close Scrap Mechanic.
2. Start JC ScrapMap and choose option 4.
3. If enabled, run option 3.
4. Confirm option 4 reports `disabled`.
5. Close map-server windows with `Ctrl+C`.
6. Delete the JC ScrapMap folder.

Deleting `mapper-data` also deletes private notes. Deleting `imports` deletes
captured roads, terrain regions, and Schematic Stations and means option 2 must
be run again when those maps are wanted.
