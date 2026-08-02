# JC ScrapMap 0.8.3-rc3

Release candidate based directly on the trusted unpacked `0.8.1-rc2`
release supplied by the user.

## Added

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
