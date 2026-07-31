# JC ScrapMap 0.7.10

This release adds an independent game-log evidence channel to the exact-road
diagnostic.

## Independent world-loading evidence

- Writes `sm.log` markers when the terrain hook executes, when the exporter
  loads, when `Generate` or `Load` is entered, and when export construction
  succeeds or fails.
- Searches Scrap Mechanic's actual `<game-folder>\Logs` directory instead of
  limiting failure evidence collection to player and AppData folders.
- Includes only JC ScrapMap marker lines from game logs in the
  privacy-conscious report.
- Retains the separate JSON hook sentinel and ordered exporter-stage history.

Together, the two channels distinguish a hook that never executed from a hook
that executed but could not write JSON output.

## Retained 0.7.9 corrections

- Grants and verifies desktop-user Modify access on the owned temporary output
  directory.
- Avoids ACL identity-translation failures.
- Safely recovers incomplete empty output directories.
- Verifies restoration and removal of all temporary game files.
