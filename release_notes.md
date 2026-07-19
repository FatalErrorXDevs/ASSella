# Release Notes - ASSella v2.2.4-alpha5

### Updater Overhaul

* **Replaced ZSync/appimageupdatetool with direct GitHub downloader:** The in-app self-updater no longer relies on appimageupdatetool, which was causing SIGABRT crashes (exit code -6) due to AppImage nesting and FUSE conflicts. The updater now queries the GitHub API directly, downloads the AppImage in 512 KB chunks with live MB/total progress, and atomically replaces the installed file.
* **Fixed missing re module import** in main_window.py that was causing the update checker background thread to silently fail.
