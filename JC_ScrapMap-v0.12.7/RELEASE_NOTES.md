# JC ScrapMap 0.12.7 — Release Notes

Português do Brasil: `RELEASE_NOTES_PORTUGUES-BR.md`

## One-time regular Warehouse revival

- Adds **Warehouse Revival** to destroyed regular Warehouses in the
  Warehouses/Schematics layer; quest Warehouses are excluded.
- Clears the exterior destruction and explosion state so the intact exterior
  returns when the save is next loaded.
- Detaches the destroyed interior floors and elevators so Scrap Mechanic can
  generate fresh interior worlds when the Warehouse is entered again.
- Preserves one-sided exterior entrance and emergency-exit portals plus a
  reconnectable normal elevator exit. This follows the game's normal
  fresh-Warehouse reconnection paths on an already-created overworld cell.
- Records each revival in mapper-owned data and refuses every later revival
  request for that Warehouse.
- Performs all save changes in one guarded SQLite transaction and verifies
  database integrity before commit.

## External Recycler

- Adds an external Recycler operated from JC ScrapMap, without installing a
  game mod or adding a native game mechanic.
- Detects one exact connected movable construction containing only seven Scrap
  Metal block cells, seven Scrap Wood block cells, one Portable Craftbot,
  three Large Chests, and two Toilet Paper parts.
- Displays detected constructions as green **Recycler** markers in a dedicated
  map layer.
- Reads installed Portable Craftbot, Workbench, and Craftbot recipes regardless
  of player unlock state.
- Recursively reduces eligible crafted items to recipe resources and returns
  50% of the aggregated resource totals, rounded down to whole items.
- Preserves items without a supported unambiguous recipe and items containing
  special instance data.

## Three-chest pooled inventory

- Treats all three Large Chests as one 90-slot output pool.
- Fills compatible existing stacks first, then free slots in deterministic
  chest order while respecting installed stack limits.
- Calculates the complete final inventory before making any edit.
- Refuses the entire operation when no eligible return is possible or when all
  output cannot fit. Partial recycling is never performed.

## Preview and transaction safety

- Adds a detailed preview listing consumed items, returned resources,
  unsupported items, and occupied slots before and after recycling.
- Requires the exact preview token during execution and rejects changed chest
  contents or a changed Recycler.
- Re-identifies the exact construction and all three linked chest containers
  immediately before writing.
- Updates the three containers inside one immediate SQLite transaction using
  compare-and-update guards.
- Runs SQLite integrity checking before commit and rolls back every change if
  any validation or write fails.

## Recycler recipe

The required connected movable construction contains exactly and only:

- 7 Scrap Metal block cells;
- 7 Scrap Wood block cells;
- 1 Portable Craftbot;
- 3 Large Chests;
- 2 Toilet Paper parts.

Items placed inside the chests do not count as attached construction parts.

## Compatibility

- Keeps Instant Recovery, manual saved-player-position updating, existing map
  layers, underground maps, and Excavation Island unchanged.
- Normal map inspection remains read-only. Only explicit Recycler execution
  and Instant Recovery write to the selected save.
- Remains offline and uses only installed game data and the selected local save.

## Validation

- Warehouse Revival passed a disposable-copy transaction test and a complete
  localhost API test. The exterior, portal, elevator, countdown, and warehouse
  registry changes were verified; the quest Warehouse remained unchanged.
- SQLite integrity passed, a second revival was refused, and the live source
  save's SHA-256 remained unchanged throughout testing.
- In-game testing confirmed the corrected exterior, fresh interiors, enemies,
  entrance elevator, internal elevator, and normal final elevator chain. It
  then exposed missing emergency-exit portals; the v3 preservation strategy
  and repair passed disposable-copy and SQLite validation, with final in-game
  emergency-exit confirmation pending.
- Hands-on testing with the intended Recycler succeeded in the target Survival
  save.
- The test batch recycled 16 items into 44 Scrap Metal, 125 Scrap Wood,
  10 Scrap Stone, 2 Pigment Flowers, and 2 Soil Bags, reducing occupied chest
  slots from 10 to 5.
- Disposable-save testing confirmed the same output, preserved the Recycler,
  and passed SQLite integrity checking.
- Automated tests passed for exact signature recognition, extra-part rejection,
  three linked 30-slot containers, 50% recursive recovery, unsupported-item
  preservation, pooled capacity refusal, stale-preview rejection, and atomic
  writes.
- Existing vehicle detection, Instant Recovery, player-position snapshot, and
  interface regressions passed.
