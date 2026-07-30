# JC ScrapMap 0.7.1

## 0.7.1 Hotfix

- Finds Scrap Mechanic across all registered Steam library folders
- No longer assumes `C:\Program Files (x86)\Steam`
- Uses the same discovery rules for Open map and terrain generation
- Requests the full installation folder if automatic helper discovery fails
- Validated with Steam and Scrap Mechanic placed in separate synthetic paths

## 0.7.0 Features

- Read-only physical Beacon import with saved icon names and colors
- Exact Desert and Burnt forest regions alongside existing Water capture
- One compact, unchecked Terrain regions control for all three region types
- Exact Schematic Stations displayed through the existing POI/spoiler layer
- Responsive main helper menu while generation runs separately
- Automatic detection and verified recovery when Scrap Mechanic exits or
  crashes before terrain capture
- Removal of the obsolete pale-green starting-area diagnostic boundary
- Existing 0.6.0 road captures remain compatible

Roads, Water, Desert, Burnt forest, physical Beacons, the responsive helper,
and crash recovery have been field-tested successfully. Schematic Station
positions require a new terrain generation and remain pending field validation.
