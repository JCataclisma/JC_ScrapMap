# Managed exact-road data

The launcher stores validated, seed-specific road files here as:

`roads-<seed>.json`

These files are generated and imported automatically by **Generate exact
roads**. Players must not copy or rename exporter output manually.

`roads-export.json` is retained as the historical `Release_01` validation
snapshot. The mapper does not load that generic filename directly.
