# JC ScrapMap 0.7.2

This usability release fixes a case where exact roads were captured correctly
but the map remained on a different Survival save.

## Changes

- Opens or refreshes the map for the exact world seed captured by the helper.
- Switches an already-running map session to the matching save.
- Warns clearly when available road data belongs to another world.
- Keeps the helper's final result visible until Enter is pressed.
- Writes `JC_ScrapMap_Diagnostic.txt` after every generation attempt.
- Adds **Open diagnostic report** to the main menu.
- Removes personal Windows folder names from the report and never includes save
  contents, player coordinates, custom notes, or Steam IDs.

The non-default Steam-library discovery fix from 0.7.1 remains included.
