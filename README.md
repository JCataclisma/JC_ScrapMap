<img width="1912" height="885" alt="JC_ScrapMap" src="https://github.com/user-attachments/assets/cde27760-88af-4222-958e-acc9fbfe95fc" />
# JC ScrapMap 0.7.1

JC ScrapMap is an offline map companion for **Scrap Mechanic 1.0 Survival**.
It reads your save without changing it and opens the map in your normal web
browser.

## Before You Start

You need:

- 64-bit Windows 10 or newer
- Scrap Mechanic 1.0 through Steam
- A modern web browser

Keep this entire folder together. Do not move individual files out of it.
No Python installation or other programming tool is required. JC ScrapMap
includes its own private runtime and does not install it into Windows.

## Start

Double-click:

`Start JC ScrapMap.cmd`

The launcher automatically finds the usual Scrap Mechanic installation and
player-save locations. If more than one player profile exists, it asks you to
choose one.

Scrap Mechanic may be installed in any Steam library. The launcher reads
Steam's registered installation and every path in
`steamapps\libraryfolders.vdf`. If helper generation still cannot locate the
game, it asks for the full Scrap Mechanic installation folder.

## The Two Main Menu Options

### 1. Open map

Use this whenever you want to view or update the map.

- It opens the selected save **read-only**.
- It refreshes the last position Scrap Mechanic wrote to the save.
- It refreshes physical player-built Beacons, including their icons and colors.
- It never enables the road helper.
- It does not require administrator permission.
- It works while Scrap Mechanic is running when the game has already written
  its latest save data.
- If the browser map is already open, it refreshes that map instead of starting
  a second map server.

The blue player symbol means **Last saved player position**. It is not live GPS:
the game decides when to write its latest position.

### 2. Generate exact roads

Normally use this **only once for each distinct Survival save seed**. If two
saves use the same seed, they can share the same road map.

Repeat it only when:

- mapping a save with a different seed;
- a future Scrap Mechanic update changes world generation; or
- an older captured map does not yet contain terrain regions or Schematic
  Stations.

Before choosing option 2, close Scrap Mechanic. Windows asks for administrator
permission because this operation temporarily adds one marked line to one
installed terrain script.

Then:

1. The launcher backs up and hashes the original script.
2. It temporarily installs the JC ScrapMap road exporter.
3. Scrap Mechanic starts.
4. Load the Survival world you want to map.
5. Wait until the launcher reports that roads, terrain regions, and Schematic
   Stations were captured.
6. Close Scrap Mechanic.
7. The launcher restores the original script, verifies its exact hash, and
   removes the temporary exporter.

After successful cleanup, ordinary Scrap Mechanic launches do not load JC
ScrapMap.

Generation runs in a separate progress window, so the main menu remains
responsive. Water, Desert, and Burnt forest cells share one unchecked
**Terrain regions** layer while retaining distinct colors. Captured Schematic
Stations use the existing unchecked POI/spoiler layer.

## If Option 2 Is Interrupted

If Scrap Mechanic exits or crashes before capture, the progress window detects
it and attempts verified automatic cleanup. If Windows, Steam, or the computer
terminates the helper window itself, close Scrap Mechanic and choose:

`3. Disable/repair road helper`

Do this before deleting the JC ScrapMap folder or launching the game again.
The recovery copy inside `.road-helper` is required until repair completes.

Option 4 shows whether the temporary road helper is currently enabled.

## Local Data

JC ScrapMap creates these folders beside the launcher:

- `imports` — exact per-seed roads, terrain regions, and Schematic Stations
- `mapper-data` — per-save map state and your private notes
- `generated` — the currently displayed browser state
- `.road-helper` — temporary recovery data used by option 2

Your Scrap Mechanic save database is never written by JC ScrapMap.

## Privacy and Networking

- Completely offline after download
- No analytics or tracking
- No advertisements
- No uploads
- No remote map server
- Browser server listens only on `127.0.0.1` on your computer
- Bundled runtime is used only from the JC ScrapMap folder

## Closing and Removing

Close a map-server PowerShell window with `Ctrl+C`.

Before removing JC ScrapMap, use option 4. If it reports `ENABLED`, close the
game and run option 3 first. When it reports `disabled`, you can delete this
entire folder. See `SAFETY_AND_REMOVAL.md` for the complete inventory.

## Source Inspection

The JC ScrapMap program is included directly as readable PowerShell, Python,
Lua, JavaScript, HTML, CSS, and JSON files. See `SOURCE.md`.

The package also includes the official 64-bit CPython 3.14.6 embeddable runtime
under `runtime/python`. Its license is included as
`runtime/python/LICENSE.txt`. Players do not install or configure it.
See `THIRD_PARTY_NOTICES.md` for its official source and verification hash.

This release does not yet declare an open-source license. Public visibility on
GitHub permits inspection but is not, by itself, permission to redistribute or
modify the code. Add an explicit license before advertising the project as
open source.
