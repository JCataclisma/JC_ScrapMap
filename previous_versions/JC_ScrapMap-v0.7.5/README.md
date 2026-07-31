# JC ScrapMap

> Exact roads are generated through an explicitly selected temporary helper.
> The launcher backs up and patches one installed terrain script, launches the
> game, captures the result, and restores the original script after the game
> closes. See the safety warning below before using it.

JC ScrapMap is an experimental, completely offline map companion for Scrap
Mechanic 1.0.

## One-click start

Download or clone the repository, then double-click:

`Start JC ScrapMap.cmd`

The menu provides:

1. **Open map** - rereads the selected save, refreshes its mapper state, and
   opens the map without changing the game. If the map is already open, its
   existing local server is refreshed instead of starting another one.
2. **Generate exact roads** - asks for Windows administrator approval,
   temporarily enables the helper, and starts Scrap Mechanic. Load the
   Survival world you want to map, then close the game when finished. The
   launcher restores the installed script, removes the temporary helper,
   imports the roads, and opens that save's map.
   After capture, JC ScrapMap validates and stores the result, then leaves a
   clear summary visible until Enter. Return to the menu and choose **Open
   map** when you are ready to view it.
3. **Disable/repair road helper** - restores the recorded original script and
   removes the mapper-owned helper after an interrupted session.
4. **Show road-helper status** - reports whether the temporary hook is active.
5. **Open diagnostic report** - opens `JC_ScrapMap_Diagnostic.txt` in Notepad.
   It contains capture stages, seed, counts, and any error, but no save contents
   or personal Windows folder names.

The launcher discovers Scrap Mechanic through Steam's registered installation
and every path in `steamapps\libraryfolders.vdf`; the game does not need to be
installed in Steam's default folder. If helper generation still cannot locate
it, the helper requests the full installation folder explicitly.

The menu remains open after an action. Map servers open in their own ordinary
PowerShell window; close a map server with `Ctrl+C` in that window. Generating
roads uses a separate elevated progress window. Its final result remains
visible until the player presses Enter, while the reusable menu remains
available.

Players do not need to install Python, copy mods, edit Lua, locate the save
database, or manage exported JSON manually. Release packages use only their
private bundled Python runtime.

### Exact-road safety warning

Generating new exact roads temporarily modifies
`Survival\Scripts\terrain\terrain_overworld.lua`. This action is never
performed by **Open map** and requires an explicit menu choice plus Windows
administrator approval.

The helper:

- Refuses activation while Scrap Mechanic is running.
- Saves the original script and its SHA-256 hash in `.road-helper`.
- Adds one marked hook and installs one mapper-owned user mod.
- Scans generated roads once when the selected world loads.
- Stores the seed-specific result under `imports`.
- Waits for Scrap Mechanic to close before restoring the script.
- Verifies exact restoration by SHA-256 and removes the temporary mod.
- Refuses to overwrite a script that changed unexpectedly.

If Scrap Mechanic exits or crashes before capture, the generation window
detects that the game process stopped and immediately attempts verified
automatic cleanup. Its diagnostic records process timing, the last exporter
stage, invalid export details, recent privacy-filtered game-log lines, and
matching Windows crash events. Each event is appended to disk immediately, and
the preceding run is retained as `JC_ScrapMap_Diagnostic.previous.txt`.
Exporter errors are contained and reported instead of being allowed to
interrupt terrain generation. If Windows, Steam, or the computer terminates
the helper window itself, choose **Disable/repair road helper** before
launching the game again.

### Persistence

Road maps are not temporary. Exact roads are stored by seed as
`imports\roads-<seed>.json` and remain usable after the game, browser, server,
and launcher close. Regenerating one seed replaces only that seed's exact-road
snapshot. Starting Scrap Mechanic normally after verified helper cleanup does
not load or run JC ScrapMap.

Road captures are matched to saves by world seed. If the selected save does
not match an available capture, the map explains that the roads belong to
another world instead of silently treating them as current.

### Asking for help

After any road-generation attempt, choose **Open diagnostic report** from the
main menu. You may send `JC_ScrapMap_Diagnostic.txt` with a bug report. This
short report does not include save contents, player coordinates, notes, Steam
IDs, or personal folder names.

Custom markers and notes will be stored outside the game under
`mapper-data\<save-identity>\markers.json`. They are a required upcoming map
feature but are not yet available in the current browser interface.

Prototype 0A proves that an external tool can:

- Discover or accept the Scrap Mechanic installation and user paths.
- Find Survival saves.
- Switch among multiple saves from the browser interface.
- Read selected save metadata using SQLite read-only mode.
- Verify that the save hash, size, and timestamp do not change.
- Assign a stable mapper identity and separate local data directory to each save.
- Generate normalized local JSON state.
- Display that state in a local, pannable and zoomable HTML interface.

The map does not provide live player telemetry. Each **Open map** action reads
the latest persisted player position from the selected save and displays it as
the **Last saved player position**. Scrap Mechanic may not flush that position
merely because the player alt-tabs, so it is deliberately not labelled current
or live.

Each **Open map** action also refreshes player-built physical Beacons from the
selected save. Their exact saved positions, configured colors, and icon types
appear in the separate **Physical beacons** layer, which starts unchecked.
Imported Beacons are read-only references and are never converted into custom
notes automatically.

The explicit terrain-generation workflow captures exact Water, Desert, and
Burnt forest cells. Their distinct colors share one unchecked **Terrain
regions** layer to keep the layer list compact. It also captures exact
Schematic Stations, which appear through the existing unchecked POI/spoiler
layer. Older road files remain usable, but newly added terrain data requires
generation again.

The map covers the complete 128 × 96-cell overworld boundary. It displays the
confirmed new-character starting position and literal fixed POI coordinates
from the active installed Survival generator. The early green diagnostic
region around the starting location has been retired; it was only a visual
boundary used during initial development and never represented terrain or a
gameplay limit.

The map can zoom out to 10 km and fit the complete overworld.

An experimental Harvestable/Unit cell-density layer was removed in 0.3.1. It
did not represent roads, terrain, current units, or reliable player discovery,
so it was not useful to the navigation product.

These anchors are not a complete terrain reconstruction and are not treated as
the current player position or discovered-state information. Engine-specific
biome, lake, and road generation remains unavailable until it can be reproduced
or exported exactly.

Displayed fixed POIs are resolved through the active `poi.lua` database to
their exact installed `.tileson` definitions. At close zoom, the map draws a
compact top-down schematic from installed entity positions. The schematic is a
structural reference, not a rendered game screenshot. Selection details retain
the original developer label, tile filename, UUID, dimensions, and entity
counts so unverified player-facing names are never presented as authoritative.

Generator anchors share one unchecked POI/spoiler layer. Their existence in
the generator does not prove that the selected character discovered them.
Discovery evidence remains diagnostic metadata and does not hide POIs.

The starting position is initially discovered. Read-only save evidence can
also classify an anchor when persisted quest state proves it was encountered.
World-loading evidence alone is not treated as a player visit. Remaining
generator anchors begin unknown and are hidden in an unchecked spoiler layer.
While that layer is temporarily enabled, a selected anchor can be marked
discovered manually.
Manual discoveries are stored per save in
`mapper-data\<save-identity>\discoveries.json`; the game save is never changed.

The interface displays `+Y` upward and `+X` to the right. Cardinal north and
east will not be assigned until the relationship between world axes and
player-facing compass direction has been verified experimentally.

## Requirements

- Windows
- Python 3.10 or newer for this development prototype
- A modern browser

The distributable version is intended to become a self-contained package that
does not require users to install Python.

## Run

From PowerShell:

```powershell
.\launcher.ps1
```

Automatic detection uses the standard Steam installation and Scrap Mechanic
user-data locations. Explicit paths can be supplied when required:

```powershell
.\launcher.ps1 `
  -GamePath 'C:\Program Files (x86)\Steam\steamapps\common\Scrap Mechanic' `
  -UserPath 'C:\Users\YourName\AppData\Roaming\Axolot Games\Scrap Mechanic\User\User_YourSteamId' `
  -Save 'C:\Users\YourName\AppData\Roaming\Axolot Games\Scrap Mechanic\User\User_YourSteamId\Save\Survival\YourSave.db'
```

The interface is served only on `127.0.0.1`. It does not contact the internet.
Press `Ctrl+C` in the launcher window to stop it.

## Generate State Without Starting the Server

```powershell
python .\scrapmap.py --no-server
```

The normalized output is written atomically to `generated\state.json`.
Each selected save also receives an independent copy under
`mapper-data\<save-identity>\state.json`. Future markers, discoveries,
breadcrumbs, and preferences will remain separated in that directory.

## Safety

- Save databases are opened with SQLite `mode=ro` and `PRAGMA query_only`.
- The selected save is hashed before and after inspection.
- Size and modification time are also checked.
- Generated files remain inside the JC ScrapMap directory.
- Manual backup names containing `Copia`, `.bak`, or `backup` are ignored during
  automatic discovery.
- No analytics, tracking, uploads, external assets, or remote services are used.
