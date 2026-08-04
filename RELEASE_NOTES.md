# JC ScrapMap 0.9.3-rc3

Runnable test candidate based on the preserved `0.9.2-rc2` candidate.

- Recognizes standard, desert, field, and forest Schematic Station tiles.
- Adds all 21 fixed and generated builder quests to the dedicated
  **Builder Quests** layer.
- Removes the Woc house and resource car quests from **All POIs / anchors**.
- Uses blue map squares for warehouses/schematic stations and yellow map
  squares for Builder Quests.

## Overlay compatibility

- Replaced the Edge-only overlay launcher with an explicit browser picker.
- Detects installed Google Chrome, Brave, Vivaldi, Chromium, Opera, and
  Microsoft Edge builds in their usual Windows locations.
- Supports manually selecting another Chromium-family browser executable.
- Remembers the choice locally and offers a normal default-browser fallback.
- Adds no browser binaries, libraries, runtimes, or installation steps.
- The regular map launcher and browser behavior remain unchanged.

## Added

- Draggable vertical dividers for resizing or nearly collapsing both side
  panels while preserving a 300-pixel minimum map width. Panel widths are
  remembered locally, and double-clicking a divider restores its default.
- An optional whole-application always-on-top companion window, launched with
  `Start JC ScrapMap Overlay.cmd`. Normal browser startup remains unchanged.

- A separate **Underground entrances** spoiler layer, disabled by default.
- Ten generator-confirmed underground surface areas: the six Grow Lab
  entrances, Scrap City, mechanic station, excavation, and the small service
  elevator.
- Entrance selection explains that underground-area maps are planned for a
  future JC_ScrapMap version.

- Exact regular 2-, 3-, and 4-floor Warehouse positions read directly from
  persisted terrain.
- A separate **Warehouses & schematic stations** spoiler layer, disabled by
  default. The fixed quest Warehouse remains in **All POIs / anchors**.
- A collapsible **Selected save** panel that remembers its open or closed
  state for the browser session.

- Exact positions of generated terrain tiles authored with a caged farmer.
- A separate **Prisoner camps** layer, disabled by default.
- Bright-orange geometric hash markers with a dark outline.
- Exact positions of ordinary lootable ruins across supported biomes.
- A separate **Ruins** layer, disabled by default, with stone-blue
  broken-wall markers.
- Exact autumn-forest cells in the existing terrain-regions layer, rendered
  with a translucent lavender-pink fill.

## Compatibility

- Saves whose `Game` table does not contain the optional `uniqueIds` column
  no longer prevent the selected world or save selector from opening.

All map extraction remains read-only and offline.
