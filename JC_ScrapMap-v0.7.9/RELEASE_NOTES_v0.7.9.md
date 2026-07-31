# JC ScrapMap 0.7.9

This release fixes cross-machine export permissions and makes world-loading
diagnostics preserve decisive evidence instead of overwriting it.

## Cross-machine output fix

- Preserves the desktop user's Windows SID across administrator elevation.
- Grants and verifies inherited Modify access only on JC ScrapMap's owned
  temporary Survival output directory.
- Enumerates ACL identities directly as SIDs, avoiding failures caused by
  unrelated Windows identities that cannot be translated to account names.
- Creates the ownership marker before ACL verification and safely recovers an
  empty directory left by an interrupted earlier activation.

## World-loading evidence

- Writes a separate terrain-hook sentinel when the appended Survival hook
  executes.
- Retains an ordered exporter-stage history instead of overwriting earlier
  evidence.
- Records entry into the terrain `Generate` or `Load` function before calling
  the original game function.
- Distinguishes hook execution, exporter loading, terrain-function entry,
  export construction, successful export, and validated capture.
- Includes every new evidence file in verified ownership cleanup.

The complete sequence was validated in-game twice against two existing
Survival worlds, followed by verified restoration of the original terrain
script and removal of all temporary files.
