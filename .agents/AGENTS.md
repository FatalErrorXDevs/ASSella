# AGENTS.md — Guidelines for ASSella Agentic Development & Releases

This file defines essential guidelines, build rules, versioning conventions, and release procedures for automated coding agents working in the ASSella repository.

---

## 1. Core Principles

- **No Hardcoded User Home Paths**: Never hardcode `/home/deck/` or `/home/<username>/`. Always use `os.path.expanduser("~")` or `Path.home()`.
- **System Inode Preservation**: When modifying SLSsteam configuration files (`~/.config/SLSsteam/config.yaml`), write updates **in-place** (`open(..., "r+")` followed by `f.truncate()`) to preserve the file's system inode and prevent breaking SLSsteam's `inotify` file watcher.
- **ACF-Independent Architecture**: ASSella writes and relies on local `metadata.json` files inside `{game_dir}/.DepotDownloader/`. Delegate `.acf` file creation/maintenance natively to Steam client via SLS config updates and `install|appid|0` named pipe signals.

---

## 2. Release & Versioning Guidelines

### A. Tag Naming Conventions
- GitHub release tags should ideally be prefixed with `v` (e.g. `v2.5.5` or `v2.5.5-beta`).
- If a release tag is created without the `v` prefix (e.g., `2.5.5`), the built-in updater handles both `v<ver>` and `<ver>` fallbacks dynamically.
- Version string in `src/res/version` should reflect the semantic version (e.g., `2.5.5`).

### B. Build Output Names & Locations
- **Local Dev Build**: `~/.local/share/ACCELA/ASSella.AppImage.dev`
- **Release AppImage Name**: `ASSella.AppImage`
- **Build Command**:
  ```bash
  ARCH=x86_64 ./appimagetool --no-appstream squashfs-root ASSella.AppImage.dev
  ```

---

## 3. Installer Script (`install.sh`) Rules

- Installer scripts MUST query GitHub API (`https://api.github.com/repos/niwia/ASSella/releases`) to dynamically resolve `browser_download_url` for `ASSella.AppImage`. This ensures both stable releases and pre-releases on the `beta` branch download correctly without throwing 404 HTTP errors.
- Always use `curl -fL` to ensure non-200 HTTP responses raise an error instead of saving HTML 404 pages as binary files.
