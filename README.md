<img width="1912" height="885" alt="JC_ScrapMap" src="https://github.com/user-attachments/assets/ab971df4-aebb-4b4d-8b45-6071269072c2" />

# JC ScrapMap 0.11.7

JC ScrapMap is an offline companion map for Scrap Mechanic Survival.

It reads generated terrain, saved positions, vehicles, progression, and other
map information directly from a selected Survival save. Version 0.11.7 also
adds an optional **Instant Recovery** action that can reposition a saved
vehicle above a specially built Rescue Vehicle.

Português do Brasil: `README_PORTUGUES-BR.md`

## Important warning: back up your save

Normal map inspection remains read-only. **Instant Recovery is different: it
edits the selected save database when you click the final recovery action.**

Before using Instant Recovery:

1. Close Scrap Mechanic completely.
2. Back up the Survival save you intend to edit.
3. Make sure the correct save is selected in JC ScrapMap.
4. Keep the backup until you have loaded and saved the recovered world
   successfully.

There is no in-app undo. If the result is not acceptable, restore your backup.

## Start

1. Extract the complete `JC_ScrapMap-v0.11.7` folder.
2. Double-click `Start JC ScrapMap.cmd`.
3. The map opens in the default browser.
4. Use **Available saves** to switch Survival worlds if necessary.

For an always-on-top companion window, use
`Start JC ScrapMap Overlay.cmd`. It can use Chrome, Brave, Vivaldi, Chromium,
Opera, Microsoft Edge, or another compatible Chromium-family browser already
installed on the computer. JC ScrapMap does not bundle or install a browser.

The bundled private Python runtime is used automatically. A separate Python
installation and administrator privileges are not required.

## Build the Rescue Vehicle

The Rescue Vehicle can be assembled in any shape or orientation. All required
parts must belong to the same connected movable creation.

It must contain exactly and only:

- 2 Scrap Gas Engines;
- 7 Scrap Metal block cells;
- 5 Scrap Wheels;
- 1 regular Scrap Seat — not the Scrap Driver's Seat;
- 1 Portable Craftbot.

Nothing else may be attached. The seven Scrap Metal blocks may be arranged in
any shape. When detected, this creation appears as a red **Rescue Vehicle**
symbol in the existing **Vehicles** layer. Regular detected vehicles remain
yellow.

## Use Instant Recovery

1. Close Scrap Mechanic and make a backup of the selected save.
2. Start JC ScrapMap and select the correct save.
3. Enable the **Vehicles** layer.
4. Confirm that the red **Rescue Vehicle** appears where you built it.
5. Click the yellow symbol of the vehicle you want to recover.
6. In the left sidebar, expand **Instant Recovery**.
7. Click **RECOVERY AT YOUR OWN RISK!** once.
8. Close JC ScrapMap, start Scrap Mechanic, and load the edited save.

The complete connected vehicle is moved so its saved reference point is seven
metres above the Rescue Vehicle. Bearings, suspensions, joined bodies,
controllers, parts, relative positions, and the vehicle's saved rotation are
preserved.

Because rotation is preserved and the vehicle is dropped above the target, it
may appear or land upside-down. This is expected. Instant Recovery does not
automatically level or rotate vehicles.

## Map features

The offline map includes, where available in the selected save:

- directional roads and terrain regions;
- water, desert, burnt forest, and autumn forest;
- Schematic Stations and regular Warehouses;
- builder quests, chemical/oil pits, prisoner camps, and ruins;
- underground entrances, progression, floor summaries, and rough floor maps;
- the separate Excavation Island surface map;
- saved player position, physical beacons, custom notes, and detected vehicles.

Most spoiler-oriented layers, including **Vehicles**, are disabled by default.

## Privacy and local data

- The web server listens only on `127.0.0.1`.
- No save, marker, coordinate, Steam ID, or map data is uploaded.
- No internet connection is required.
- Map inspection opens the save read-only.
- Only the explicit Instant Recovery action opens the selected save for an
  atomic local edit.
- Generated map state, mapper notes, browser preferences, and operational logs
  remain inside the extracted application folder.

## Logs

The PowerShell window remains open while the local server is running. Closing
that window stops JC ScrapMap.

Operational events are written to `logs\jc-scrapmap.log`. The rotating log
does not include save contents, Windows usernames, Steam IDs, save filenames,
full personal paths, player coordinates, custom-note contents, or HTTP request
bodies.

## Recovery limitations

- Recovery uses the last state written to the save; it is not a live game
  teleport.
- Scrap Mechanic should be closed while the save is edited.
- The selected creation must still match the vehicle shown on the map.
- Exactly one valid Rescue Vehicle must exist in the selected save.
- Vehicle orientation is preserved, so an upside-down result is possible.
- Restore your backup if the world or creation does not behave as expected.
