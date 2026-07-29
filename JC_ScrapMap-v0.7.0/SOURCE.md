# Source and Audit Guide

JC ScrapMap 0.7.0 ships as readable source code.

## Entry Points

- `Start JC ScrapMap.cmd` — double-click entry point
- `launcher.ps1` — starts the menu or map process
- `road-helper.ps1` — exact-road activation, recovery, and launcher menu
- `scrapmap.py` — read-only save inspection, normalized state, and local server

`launcher.ps1` invokes only `runtime/python/python.exe`; it does not search for
or require Python installed on the player's computer.

## Browser Interface

- `web/index.html`
- `web/app.css`
- `web/app.js`

## Temporary Road Exporter

- `game-side/mod/description.json`
- `game-side/mod/Scripts/terrain_road_export.lua`

The Lua exporter reads generated roads, terrain-region flags, and exact
Schematic Station POI cells once, then writes a compact JSON result into its
mapper-owned mod directory. It does not call `sm.storage.save` or
`sm.terrainData.save`.

## Intentionally Excluded from the Release

- Developer research and test fixtures
- Python caches
- Personal mapper identities
- Save-derived generated state
- Private markers and discoveries
- Captured maps from the developer's saves
- Active recovery state and installed-script backups
- Experimental external road-reconstruction scripts

## Licensing Status

The source is included for transparency and auditing. No open-source license
has been selected in this release folder. The repository owner should add a
license before describing the project as open source or inviting code reuse.

The bundled CPython runtime is a third-party component distributed under the
Python Software Foundation license. Its original `LICENSE.txt` is included
unchanged inside `runtime/python`.
