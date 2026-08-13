# JC ScrapMap 0.11.7 — Release Notes

Português do Brasil: `RELEASE_NOTES_PORTUGUES-BR.md`

## Rescue Vehicle and Instant Recovery

- Adds exact Rescue Vehicle recognition to the existing **Vehicles** layer.
- Requires exactly two Scrap Gas Engines, seven Scrap Metal block cells, five
  Scrap Wheels, one regular Scrap Seat, and one Portable Craftbot, with no
  additional attached parts or blocks.
- Allows the required parts to be arranged in any shape or orientation.
- Displays the Rescue Vehicle with a red map symbol and the label
  **Rescue Vehicle**; regular detected vehicles remain yellow.
- Adds an expandable **Instant Recovery** control after selecting a detected
  vehicle.
- **RECOVERY AT YOUR OWN RISK!** moves every connected rigid body belonging to
  the selected vehicle to a saved reference position seven metres above the
  Rescue Vehicle.
- Preserves relative body positions, joints, bearings, suspensions,
  controllers, attached parts, and saved rotation.

## Important save-editing warning

Normal map generation and inspection remain read-only. Instant Recovery is an
explicit exception and writes directly to the selected Survival save.

Close Scrap Mechanic and back up the selected save before using recovery.
There is no automatic undo. Restore the backup if the edited world or vehicle
does not behave as expected.

Rotation is intentionally preserved. A recovered vehicle can appear or land
upside-down; the feature does not automatically level it.

## Reliability and compatibility

- Re-identifies the selected vehicle and exact Rescue Vehicle immediately
  before editing instead of trusting stale browser state.
- Applies one common translation to all connected vehicle bodies inside an
  immediate SQLite transaction.
- Updates the saved rigid-body transforms and SQLite spatial bounds together.
- Runs SQLite integrity checking before committing the edit.
- Rejects stale selections, missing vehicles, unsupported records, and saves
  without exactly one valid Rescue Vehicle.
- Keeps all existing map layers and the separate Excavation Island and
  underground views unchanged.

## Validation

- Exact signature, block-volume, and extra-part rejection tests passed.
- Multi-body translation preserved rotations, construction records, and the
  Rescue Vehicle in automated disposable-save testing.
- Python, JavaScript, launcher, map-layer regression, archive-content, and
  bundled-runtime refresh checks passed.
- Hands-on recovery testing succeeded. An upside-down landing was observed and
  accepted as expected rotation-preserving behavior.
