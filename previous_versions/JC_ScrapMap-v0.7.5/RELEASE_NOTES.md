# JC ScrapMap 0.7.5

This release makes exact-road failures actionable and prevents exporter errors
from escaping into Scrap Mechanic terrain generation.

## Diagnostics and resilience

- Creates the current-run diagnostic before helper activation and appends every
  redacted event directly to disk as it happens.
- Preserves the preceding run as `JC_ScrapMap_Diagnostic.previous.txt`.
- Marks a newly started run as `IN PROGRESS`; success or error is a final
  timestamped result entry, so abrupt termination leaves usable evidence.
- Records Steam launch time, detected Scrap Mechanic process IDs and lifetime.
- Writes and monitors exporter stages: loaded, waiting, exporting, exported,
  or error.
- Reports malformed or semantically invalid export files instead of silently
  ignoring them.
- On early game exit, includes recent privacy-filtered game-log tails and
  matching Windows Application Error events when available.
- Adds the PowerShell script stack trace to failed-generation reports.
- Runs road extraction behind a Lua protected call, logs the exact exporter
  error, and leaves the game's original Generate/Load result intact.
