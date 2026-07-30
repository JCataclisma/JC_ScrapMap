# JC ScrapMap 0.7.4

This release fixes `Unknown save identity` errors when switching between
multiple Survival saves.

## Cause and fixes

- Save identity no longer depends on Scrap Mechanic's mutable `uniqueIds`
  database field.
- The server refreshes the discovered save list and resolves identities from
  current save metadata whenever a save is selected.
- Existing mapper-owned markers and discovery choices are copied forward from
  matching older identity folders when possible. Old folders are retained.
- The launcher verifies that a running localhost map server belongs to the
  same extracted JC ScrapMap folder. It no longer silently connects to a
  different unpacked copy using port 8765.
- The atomic road-import and final-file validation fix from 0.7.3 is included.
- Road generation does not open the map automatically.

Validation cycled all five detected Survival saves forward and backward through
a live server for ten consecutive switches without an identity error.
