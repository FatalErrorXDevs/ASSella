# Release Notes - ASSella v2.2.3-rc1

Welcome to v2.2.3-rc1 in the preview/beta branch. This release introduces a persistent retro LCD status pager, streamlined UI layout during active tasks, QSettings reset fixes, and major backend upgrades to the ASShead config fixer.

### Features & Layout Changes

* **Persistent Status Pager:**
  - Added a full-width retro LCD/pager status bar at the top of the interface.
  - Automatically loads and integrates custom monospace and typewriter fonts ("Sonic 1 HUD Font" and "TrixieCyrG-Plain") with standard system fallbacks.
  - Actively listens to internal logging streams and formats major events (connecting, downloading, DRM removal, achievements generation) in uppercase.
  - Persistently displays the last status message when the queue is idle instead of reverting to a blank state.

* **Streamlined UI Layout:**
  - Automatically collapses the Hubcap API Stats card to a single line above the progress bar during active operations.
  - Automatically hides the Library Update button and the Steam/SLS Status card when active download or installation tasks are running to optimize layout spacing.

### Bug Fixes & Stability

* **QSettings Reset Fix:**
  - Implemented a custom RobustQSettings handler to resolve standard PyQt6 settings parsing bugs. This prevents stored settings (such as "Generate Achievements" or "Use Steamless") from randomly resetting or toggling themselves.

### Backend Upgrades

* **ASShead Configuration Fixer:**
  - Fully updated to support the latest SLSsteam settings.
  - Added support for new keys: DisableUpdates, DepotBlacklist, and ManifestIds.
  - Implemented 64-bit digit validation for Manifest IDs.
  - Built a lenient salvage block parser to rescue unindented or malformed keys in config.yaml rather than silently deleting them.
