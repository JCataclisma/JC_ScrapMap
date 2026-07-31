# JC ScrapMap 0.7.7

This release replaces the broken 0.7.6 duplicate-load guard after two
successful in-game tests against both a new world and an existing world.

## Loader correction

- Removes `rawget`, which is unavailable in Scrap Mechanic's restricted Lua
  runtime and stopped the exporter before its first `loaded` status.
- Uses a direct sandbox-global guard to prevent duplicate wrapping within the
  same terrain-script context.
- Runs the exporter `dofile` through `pcall`.
- Persists a `loader-error` status containing the actual Lua error if the
  exporter cannot load.

## Retained 0.7.6 improvements

- Uses the portable `$SURVIVAL_DATA` exporter instead of a profile-mounted
  `$CONTENT_<UUID>` local mod.
- Keeps a unique, permanent, immediately flushed diagnostic for every run.
- Redacts Steam profile IDs.
- Waits for exported JSON to stabilize before parsing.
- Announces validated capture while the game remains open.
- Restores and verifies all temporary game files after the game closes.
