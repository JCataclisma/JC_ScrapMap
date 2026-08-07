# JC ScrapMap 0.9.7

JC ScrapMap is an offline companion map for Scrap Mechanic Survival.

This release reads exact generated terrain directly from the selected save
database. It does not modify Scrap Mechanic, launch the game, install Lua
files, or require administrator privileges.

## Start

1. Extract the complete folder.
2. Double-click `Start JC ScrapMap.cmd`.
3. The map opens in the default browser.
4. Use the save selector in the map to switch Survival worlds.

For an always-on-top companion window, double-click
`Start JC ScrapMap Overlay.cmd`. Choose any detected supported Chromium-family
browser, or select another compatible browser executable. The picker supports
Google Chrome, Brave, Vivaldi, Chromium, Opera, and Microsoft Edge; only a
browser already installed on the computer is used. No browser is bundled or
installed by JC ScrapMap. The overlay is most reliable while Scrap Mechanic is
running in Borderless Windowed mode.

The overlay remembers the selected browser inside the extracted JC ScrapMap
folder and asks again on every launch, with the previous choice as the default.
Its normal-browser fallback does not use always-on-top mode.

Drag the map's left and right dividers to resize or nearly collapse the side
panels. Double-click either divider to restore that panel's default width.
Panel widths are remembered in the browser.

The bundled private Python runtime is used automatically. No Python
installation is required.

## Exact map data

The regular overworld terrain stored by Scrap Mechanic contains the generated
cell flags and terrain UIDs. JC ScrapMap reads these values using SQLite
read-only mode and displays:

- directional roads;
- water/lake regions (BLUE areas);
- desert regions (TAN/LIGHT BROWN areas);
- burnt-forest regions (BROWN areas);
- autumn-forests (LIGHT PURPLE/PINK areas);
- Schematic Stations;
- regular 2-, 3-, and 4-floor Warehouses.

Regular Warehouses and Schematic Stations share the unchecked **Warehouses &
schematic stations** spoiler layer. The fixed quest Warehouse remains in
**All POIs / anchors**.

The selected save is hashed before and after inspection. Map generation fails
if its size, timestamp, or SHA-256 changes during the operation.

## Privacy and offline behavior

- The local web server listens only on `127.0.0.1`.
- No save, marker, coordinate, Steam ID, or map data is uploaded.
- No internet connection is required.
- The selected save is never opened for writing.
- Mapper notes and generated browser state remain inside this extracted
  application folder.

## Live and persistent logs

The PowerShell window remains open while the local map server is running and
shows live operational events. Closing that window stops the server.

The same operational events are retained in:

`logs\jc-scrapmap.log`

The log rotates at 1 MB and retains three backups. It records version,
auto-detection results, hashed mapper identity, seed, terrain counts, refresh
and save-switch activity, integrity results, local HTTP paths, server
lifecycle, and error categories.

It does not record save contents, Windows usernames, Steam IDs, save
filenames or full paths, player coordinates, marker or note contents, HTTP
request bodies, or decoded terrain contents.

## No helper or recovery workflow

This package intentionally contains no road helper, terrain hook, exporter,
administrator prompt, recovery backup, or game-side diagnostic workflow. The
previous helper-based releases remain separate and are not modified by this
release.

## Release-candidate status

This is the `0.9.7` working version. Prisoner camps and ordinary
lootable ruins remain in their existing separate layers. Selected-save details
can be expanded or collapsed to leave more room for layer controls. The new
Underground entrances layer identifies surface access areas; underground maps
are reserved for future versions.
