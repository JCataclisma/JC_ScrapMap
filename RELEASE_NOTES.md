# JC ScrapMap 0.8.0-rc1

This release candidate replaces the temporary in-game terrain
exporter workflow with direct read-only extraction of Scrap Mechanic's
persisted overworld terrain.

## Included

- Exact roads and direction masks from the selected save.
- Exact water, desert, and burnt-forest regions.
- Exact Schematic Station cells.
- Existing save switching, player position, beacons, markers, discoveries,
  local browser map, and offline behavior.
- Bundled private Python runtime.
- Live PowerShell operational output plus a privacy-conscious rolling log.

## Removed from this release workflow

- Administrator elevation.
- Installed terrain-script patching.
- Temporary Lua exporter installation.
- Scrap Mechanic launch and process monitoring.
- Road-capture imports, recovery state, and game-side diagnostic reports.

The previous 0.7.10 source and release remain unchanged elsewhere in the
project.
