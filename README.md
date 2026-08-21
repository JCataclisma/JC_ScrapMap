<img width="1912" height="885" alt="JC_ScrapMap" src="https://github.com/user-attachments/assets/ab971df4-aebb-4b4d-8b45-6071269072c2" />

# JC ScrapMap 0.12.7

JC ScrapMap is an offline companion map for Scrap Mechanic Survival.

It reads generated terrain, saved positions, vehicles, progression, and other
map information directly from a selected Survival save. Version 0.12.7 adds a
one-time revival action for destroyed regular Warehouses. It restores the
exterior and lets the game create fresh interior floors. Quest Warehouses are
never eligible.

Português do Brasil: `README_PORTUGUES-BR.md`

## Important warning: back up your save

Normal map inspection remains read-only. **Warehouse Revival, Recycler
execution, and Instant Recovery are explicit save-editing actions.**

Before using either action:

1. Close Scrap Mechanic completely.
2. Back up the Survival save you intend to edit.
3. Make sure the correct save is selected in JC ScrapMap.
4. Keep the backup until you have loaded and saved the edited world
   successfully.

There is no in-app undo. If the result is not acceptable, restore your backup.

## Start

1. Extract the complete `JC_ScrapMap-v0.12.7` folder.
2. Double-click `Start JC ScrapMap.cmd`.
3. The map opens in the default browser.
4. Use **Available saves** to switch Survival worlds if necessary.

For an always-on-top companion window, use
`Start JC ScrapMap Overlay.cmd`. It can use Chrome, Brave, Vivaldi, Chromium,
Opera, Microsoft Edge, or another compatible Chromium-family browser already
installed on the computer. JC ScrapMap does not bundle or install a browser.

The bundled private Python runtime is used automatically. A separate Python
installation and administrator privileges are not required.

## Build the Recycler

All required parts must belong to one connected movable creation. Its shape
and orientation do not matter.

It must contain exactly and only:

- 7 Scrap Metal block cells;
- 7 Scrap Wood block cells;
- 1 Portable Craftbot;
- 3 Large Chests;
- 2 Toilet Paper parts.

Nothing else may be attached. Items stored inside the three chests are
contents, not attached construction parts, and therefore do not invalidate the
Recycler. When detected, it appears as a green **Recycler** symbol in its own
map layer.

## Use the Recycler

1. Put the items to recycle inside any of the three Large Chests.
2. Close Scrap Mechanic and back up the selected save.
3. Start JC ScrapMap and select the correct save.
4. Select the green **Recycler** marker.
5. Expand **External Recycler** and click **Preview recycling**.
6. Verify the listed inputs, returned resources, and chest capacity.
7. Click **RECYCLE AT YOUR OWN RISK!** only if the preview is correct.
8. Close JC ScrapMap, start Scrap Mechanic, and load the edited save.

The Recycler reads installed Portable Craftbot, Workbench, and Craftbot recipe
files, regardless of which recipes the player has unlocked. Craftable items
are recursively reduced to their underlying recipe resources. After all
eligible inputs are combined, the Recycler returns 50% of each resource total,
rounded down to whole items.

The three Large Chests form one pooled 90-slot inventory. Existing compatible
stacks are filled first, followed by empty slots across all three chests.
Unsupported items remain in their original slots. If no item is recyclable,
or if every returned resource cannot fit, nothing is changed. A changed or
stale preview is also rejected. Successful recycling updates all three chests
in one atomic transaction and performs a SQLite integrity check before commit.

## Update the saved player position

1. Select the blue **Last saved player position** marker.
2. Click **Update saved player position** in the left sidebar.

The app makes a disposable local snapshot and reads only the player record.
The marker and timestamp update without rebuilding the complete map. This is
the newest position written to the save, not a live in-memory position.

## Build the Rescue Vehicle

The Rescue Vehicle must contain exactly and only:

- 2 Scrap Gas Engines;
- 7 Scrap Metal block cells;
- 5 Scrap Wheels;
- 1 regular Scrap Seat — not the Scrap Driver's Seat;
- 1 Portable Craftbot.

All parts must form one connected movable creation. It appears as a red
**Rescue Vehicle** symbol in the **Vehicles** layer.

## Use Instant Recovery

Close Scrap Mechanic, back up the save, select the yellow vehicle marker, open
**Instant Recovery**, and click **RECOVERY AT YOUR OWN RISK!**. The complete
connected vehicle is moved seven metres above the Rescue Vehicle while its
parts, joints, relative positions, controllers, and saved rotation are
preserved. Because rotation is preserved, it may appear or land upside-down.

## Map features

The offline map includes, where available:

- directional roads and terrain regions;
- water, desert, burnt forest, and autumn forest;
- Schematic Stations and regular Warehouses;
- builder quests, chemical/oil pits, prisoner camps, and ruins;
- underground entrances, progression, floor summaries, and rough floor maps;
- the separate Excavation Island surface map;
- saved player position, physical beacons, custom notes, detected vehicles,
  Rescue Vehicle, and Recycler.

## Privacy and local data

- The web server listens only on `127.0.0.1`.
- No save, marker, coordinate, Steam ID, or map data is uploaded.
- No internet connection is required.
- Normal map inspection opens the save read-only.
- Player-position updates read only a disposable local snapshot.
- Only explicit Recycler execution and Instant Recovery open the selected save
  for an atomic local edit.
- Generated map state, mapper notes, browser preferences, and operational logs
  remain inside the extracted application folder.

## Logs

The PowerShell window remains open while the local server is running. Closing
that window stops JC ScrapMap.

Operational events are written to `logs\jc-scrapmap.log`. The rotating log
does not include save contents, Windows usernames, Steam IDs, save filenames,
full personal paths, player coordinates, custom-note contents, or HTTP request
bodies.

## Save-editing limitations

- Scrap Mechanic must remain closed while the save is edited.
- Both actions use the last state written to the save, not live game memory.
- The selected construction must still match what was shown in the preview.
- Recycler output uses supported installed crafting recipes and whole-item
  rounding; unsupported items are preserved.
- Instant Recovery preserves vehicle orientation, including upside-down
  orientations.
- Restore your backup if the edited world does not behave as expected.
