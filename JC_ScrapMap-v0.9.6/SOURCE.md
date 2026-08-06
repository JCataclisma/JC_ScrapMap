# Source and Audit Guide

JC ScrapMap 0.9.6 is provided as readable source code.

## Entry points

- `Start JC ScrapMap Overlay.cmd` — browser-selecting overlay entry point

- `Start JC ScrapMap.cmd` — double-click entry point
- `launcher.ps1` — starts the bundled application directly
- `scrapmap.py` — read-only save inspection, map state, and local server
- `terrain_reader.py` — persisted terrain Lua-object decoder

Operational logging is implemented in `scrapmap.py` with Python's standard
rotating file handler.

The launcher invokes only the bundled `runtime/python/python.exe`.

## Browser interface

- `web/index.html`
- `web/app.css`
- `web/app.js`

## Intentionally absent

- `road-helper.ps1`
- game-side Lua hooks or exporters
- imported per-seed road captures
- administrator-elevation workflow
- recovery state and game-side diagnostic reports

## Intentionally excluded

- Developer saves and research fixtures
- Python caches
- Generated state
- Personal mapper identities, markers, and discoveries

## Runtime

The bundled CPython runtime is a third-party component distributed under the
Python Software Foundation license. Its original license is included at
`runtime/python/LICENSE.txt`.
