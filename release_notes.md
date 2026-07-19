# Release Notes - ASSella v2.2.4-alpha6

### Updater Fix

* **Fixed ZSync delta updates:** The in-app self-updater now correctly uses delta updates via appimageupdatetool. The previous SIGABRT crashes were caused by a wrong asset filename pattern (`ASSella-x86_64.AppImage.zsync` instead of `ASSella.AppImage.zsync`) in the update info string. This is now fixed in the build scripts and updater code.
* **Fallback to full download:** If delta update fails for any reason, the updater automatically falls back to downloading the full AppImage with live MB progress display.
