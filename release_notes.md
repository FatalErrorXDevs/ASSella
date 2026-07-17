# Release Notes - ASSella v2.2.3

Welcome to v2.2.3. This release introduces a persistent retro LCD status pager, streamlined UI layout during active tasks, QSettings reset fixes, critical thread-safety and timeout bug fixes, and major backend upgrades.

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

* **Critical gevent Timeout & Crash Fixes:**
  - Caught `BaseException` (specifically `gevent.timeout.Timeout`) in `batched_get_product_info` to prevent Steam connection drops from crashing the update-check task.
  - Extended `Worker.run` to catch `BaseException` so any uncaught thread-level gevent timeout gracefully aborts and cleans up resources without leaking threads or lockups.
  
* **Deadlock Prevention:**
  - Wrapped achievement check threads with fallback values so network failures do not drop signals and permanently hang/deadlock the job queue.
  - Closed download process stdout pipes immediately after output reading is finished, preventing descriptor exhaustion and thread leaks on cancel.

* **Shutdown Synchronization:**
  - Forced synchronous saving of the update status cache on application exit, resolving race conditions where background save threads could execute after main context destruction.

### Performance & Backend Upgrades

* **Depot Description Parsing Cache:**
  - Implemented a module-level cache for `depots.ini`, avoiding the repetitive parsing of 146K configuration entries on every single ZIP processing task (massive CPU and memory footprint reduction).

* **ASShead Configuration Fixer:**
  - Fully updated to support the latest SLSsteam settings.
  - Added support for new keys: DisableUpdates, DepotBlacklist, and ManifestIds.
  - Implemented 64-bit digit validation for Manifest IDs.
  - Built a lenient salvage block parser to rescue unindented or malformed keys in config.yaml rather than silently deleting them.
