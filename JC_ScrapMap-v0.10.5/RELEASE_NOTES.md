# JC ScrapMap 0.10.5

- Corrects fixed-generator POI placement so markers are centered on their
  actual multi-cell footprint.
- Adds a dedicated always-visible Excavation Island surface map based on the
  installed fixed island world.
- Shows the saved elevator connection, authored terrain and contents, ruins,
  loot points, enemy spawns, and saved physical beacons within the island.
- Adds mouse-wheel and simple `+` / `-` zoom controls exclusively to the
  Excavation Island map.

# JC ScrapMap 0.9.7

- Finds movable engine-less creations that contain both a driver's seat and a
  sport or off-road suspension.

- Keeps the disabled-by-default **Vehicles** layer for movable creations with
  gas/electric engines and now also recognizes the seat + suspension signature.
- Excludes fixed, ground/world-connected engine-bearing objects to avoid
  incorrectly marking doors and other machinery as vehicles.
- Keeps engine-powered creations attached to a lift eligible, helping locate
  vehicles that were thrown far away during lift collisions.
- Shows the selected vehicle's detected signature, position, and identification
  details in the lower-left information panel.
- Adds an expandable underground-floor panel beneath Available saves.
- Shows saved Vault value, next access-card target, and remaining value.
- Lists all eight main underground depths with generated, accessible, reached,
  and locked status.
- Opens generated floors in separate rough-map tabs showing the complete floor
  extent and saved voxel/resource activity cells.

Release based on the preserved `0.9.3-rc3` release.

- Adds a disabled-by-default **Chemical & Oil Pits** layer.
- Shows exact 1x1 and 2x2 chemical/crude-oil terrain placements as violet
  circles while preserving all existing layers.

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
