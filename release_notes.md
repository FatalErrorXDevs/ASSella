# Release Notes - ASSella v2.2.4-rc1

Welcome to v2.2.4-rc1. This pre-release introduces automated SLSsteam updates, a default download location manager, search list rendering performance improvements, consolidated DRM controls, and customizable filtering toggles.

### SLSsteam Integration & Updater

* **Automated Updates Check:**
  - Performs an automated background check for SLSsteam updates on application boot.
  - Automatically queries the GitHub Releases API to detect if the local SLSsteam version is outdated.
* **SLSsteam Updater UI & Actions:**
  - Added a dashboard status row showing whether SLSsteam is up-to-date (green), outdated (orange), or not found (red).
  - Built an installer task to automatically download the latest SLSsteam archive, extract it using 7z, and write local metadata version files.
  - Prompts first-time users without an SLSsteam install to run the updater automatically.
* **Headcrab Setup:**
  - Integrated Headcrab installer setups directly into the SLS settings tab.

### Default Download Locations

* **Steam Library Selection:**
  - Added a dropdown selector in Settings populated with detected Steam libraries and custom folder paths.
  - Automatically saves the chosen library as the default download location.
  - Bypasses folder browse prompts during new game installations, installing directly into the chosen default directory.

### Performance & Search Optimizations

* **Search Performance & Lag Fix:**
  - Resolved UI thread blockage and lag when typing searches rapidly (especially for short terms like "war" or "wae").
  - Separated network-heavy cover image fetches from the main query list rendering logic.
  - Game search results now render instantly, with image downloads deferred using a short delay timer and loaded one-by-one in the background. This guarantees 100% UI responsiveness for search productivity.
* **Clean Settings Layout:**
  - Removed visible description labels beneath settings checkboxes in favor of hover tooltips. This provides a compact, clean, and perfectly aligned settings window.
  - Restored core selection and LanCache checkboxes back to the main ASSella settings tab.
* **DRM Remover Consolidation:**
  - Consolidated Steamless CLI and Steamless AIO options into a single compact dropdown.
  - Renamed the achievements option to "Generate Achievements (Recommended Off)", moving description text to hover tooltips.

### Customizable Filters

* **Soundtrack and OST Depots:**
  - Added a settings toggle to filter out soundtracks and OSTs during downloads. Disabling the filter allows downloading soundtrack-themed depots.
* **Search Blacklist Keywords:**
  - Added a settings toggle to enable or disable filtering of blacklisted keywords in manifest search results.
