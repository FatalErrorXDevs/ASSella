# Release Notes - ASSella v2.2.4-alpha1

### In-App Self-Updater (ZSync Delta Updates)

* **Click-to-Update:** The "Update Available" indicator in the bottom titlebar is now clickable. Clicking it opens an update prompt that downloads and applies the new version using ZSync delta patching, downloading only the changed blocks instead of the full AppImage.
* **Accurate Version Targeting:** The updater now targets the exact release version found during the update check, ensuring beta and alpha channel builds correctly pull from their respective pre-release tags rather than the latest stable release.
* **Tool Update Version Comparison:** Fixed tool update detection to use semantic version tuple comparison instead of string equality, preventing false "update available" notifications after changelog-only edits on GitHub.

### Credits & Updates Dialog

* **Redesigned layout:** Credits dialog now uses clearly separated sections with small uppercase category labels for Developer, Contributors, and Third-Party Tools.
* **Branch badge:** The dialog header now shows a colored pill badge indicating the active release channel (BETA in orange, ALPHA in green, MAIN in blue), derived automatically from the version string.
* **Contributor credits:** Added drazy and morrenus as named contributors. Third-party tools listed separately in a muted grid.
* **In-dialog update check:** A "Check for Updates" button is integrated directly into the Credits dialog with live status feedback. Clicking "Install Update" from the results triggers the ZSync updater flow.

### Build Pipeline

* **ZSync-enabled AppImage packaging:** Build and release scripts now use the official appimagetool with embedded ZSync update information. Both the AppImage and its matching .zsync checksum file are uploaded to GitHub releases.
* **Workspace release rules:** Added AGENTS.md to the workspace customization root to persist release conventions (versioning, no-emoji changelogs, ZSync packaging) for future release sessions.
