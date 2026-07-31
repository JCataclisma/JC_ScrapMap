# JC ScrapMap 0.8.1-rc2

Release candidate based on the direct-save `0.8.0-rc1` approach.

## Added

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
