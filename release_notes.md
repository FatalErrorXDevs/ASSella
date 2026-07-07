## ASSella v2.0d (Release candidate 5) — Changes from v2.0d RC4

*   **Fixed Post-Download Achievements Hang**: Added a background watchdog thread with a strict 25-second timeout to the achievements schema extraction task. This prevents unconfigured or expired Steam Guard sessions from hanging the achievements generation process (and the overall installation) indefinitely at "waiting for achievements".

---

## ASSella v2.0d (Release candidate 4) — Changes from v2.0d RC3

*   **Fixed Queue Stuck Race Condition**: Fixed a critical race condition in Qt signal connection order where fast-finishing background tasks (such as Steam achievements generation or ZIP extraction) could complete before their `cleanup_complete` signal handler was connected, causing the job queue to hang indefinitely.

---

## ASSella v2.0d (Release candidate 3) — Changes from v2.0d RC2

*   **Fixed Update Job Deletion Vulnerability**: Restructured download cancellation behavior to check for pre-existing installations *prior* to starting a download. This ensures canceling an update or additional depot download preserves existing game files and their `.acf` manifests, rather than deleting the entire installation.

---

## ASSella v2.0d (Release candidate 2) — Changes from v2.0c

*   **One-time Achievements Terminal Setup**: Swapped out the settings GUI textboxes for Steam credentials with a secure interactive terminal window setup button. This aligns with the old SLScheevo workflow and handles Steam Guard (2FA) verification prompts cleanly in a visible terminal.
*   **Persistent & Sandbox-Resilient Encryption**: Upgraded credentials encryption from using a volatile MAC-address key to deriving keys from a persistent machine ID (`/etc/machine-id` on Linux, `MachineGuid` registry key on Windows). Includes an automatic fallback decryptor for backwards compatibility with existing cached MAC-address credentials.
*   **Robust .NET 9 Environment Resolution**: Integrated dynamic resolution of locally-installed `.NET` runtimes (e.g., inside `/home/deck/.dotnet` on Steam Deck/SteamOS). Sets `DOTNET_ROOT` and prepends the path to `PATH` dynamically, resolving standard host execution errors inside the AppImage container environment.
*   **CLI Setup Menu**: Replaced the automated all-games schema download with an interactive 5-option command-line interface. Users can choose to perform setup, download all schemas, download schemas for a specific game, clear stored credentials, or exit.
*   **Quick Verification AppID**: Changed credentials verification from checking all games to running against Spacewar (AppID `480`), ensuring the login setup finishes successfully in just 2 seconds.
*   **Aesthetics & Performance Optimizations**: Refactored the new game library view list population, batch-caching search layouts, and connection caching to reduce startup lag and UI interaction lag significantly.

---

## ASSella v1.9c (Release candidate 1) — Changes from v1.9b

*   **Manifest Cache Age & Status Display**: The Game Library screen now displays the age and status of cached game manifests (e.g., `Manifest: Cached (1-24hrs ago)`, `Manifest: Cached (1-3days ago)`, or `Manifest: Fetching...` if it is currently updating or missing).
*   **Automatic Cache Refresh**: Completing a download or update now automatically refreshes the local SQLite manifest cache timestamp, updating the manifest age status instantly in the Game Library screen.
*   **Thread-Safe Download Speed Monitor**: Reworked the speed monitor task to connect directly to the GUI elements via `Qt.ConnectionType.QueuedConnection`, securing the app against PyQt cross-thread abort crashes.
*   **Simplified Download Display**: Completely removed ETA and size progress calculation logic to maintain a clean layout displaying only the download speed alongside play/pause/stop controls.

---

## ASSella v1.9b (Release candidate 1) — Changes from v1.9a

*   **Unrestricted Fetching**: Removed the blacklist filtering for manifest downloading. Tags and media variants previously restricted are now available to fetch.
*   **Minimal Boot Window**: Resized the initial application window upon startup to be significantly smaller and less intrusive instead of displaying all prior update history prominently at boot.
*   **Config Resilience**: The config parser relies natively on `QSettings` ignoring keys that are not requested. It is fully backwards-compatible with ACCELA's config layout and gracefully handles and ignores obsolete `[GIFs]` and audio settings. Transitioning from ACCELA to ASSella is completely conflict-free.

---

## ASSella v1.9a (Release candidate 1) — Changes from v1.8g

**[REUPLOAD / HOTFIX 2]**: Fixed two critical crashes caused by orphaned GIF manager calls:
1. `AttributeError` on `switch_to_download_gif()` after selecting a library.
2. `AttributeError` on `show_main_gif()` occurring immediately after a download/installation successfully finishes.

### 1. Remote Web UI & Headless Mode
*   **Web Server & UI**: Access and control your ASSella client over a web interface on the local network (port `8765` by default). Features a beautiful themed layout matching ASSella's aesthetic.
*   **Background Service**: Built-in Systemd background user service management integration in the Settings dialog (Start/Stop service, and Enable/Disable on boot).
*   **Smart Selection & Cache Reuse**: Seamlessly skip depot confirmation dialogs remotely and reuse cached ZIP files when queueing downloads.

### 2. Complete Asset & Dependency Pruning
*   **GIF & Sound Removal**: Completely removed the animation panel, all `.gif` files, `.wav`/`.mp3` clips, settings toggles/sliders, and deleted the underlying GIF and audio manager classes.
*   **Unused Dependencies**: Removed `numpy`, `pillow` (Pillow), and `just_playback` from python requirements to keep the package light and slim.
*   **Style Dialog Removal**: Removed the duplicate and unused `StyleDialog` to clean up the dialog codebase.

### 3. Stability & Concurrency Optimizations
*   **Memory Leak Guards**: Migrated the log widget from `QTextEdit` to `QPlainTextEdit` with a strict `5000` line history limit. Enabled a `RotatingFileHandler` for logs, capping individual log files at 5MB with a maximum of 3 rotating backups.
*   **Sequential Download Stalling Fix**: Migrated from a simple boolean conductor flag to a step-by-step state machine tracker. This guarantees sequential downloads advance correctly past 100% and proceed to post-processing without stalling.
*   **Connection Reuse**: Upgraded the steam metadata fetcher to share a single `SteamClient` connection across batches with a localized fallback.
*   **File I/O debouncing**: Coalesced high-frequency status cache writes using a debounced timer.
*   **Offscreen & DRM fixes**: Corrected executable globbing pattern behavior for offscreen execution under temporary mount points. Steamless completion signal now fires once-per-game rather than per-file.

---

## ASSella v1.8g — Changes from v1.8f

### Installer Script — Interactive Menu

The install.sh is now a fully interactive menu-driven installer with four options:

  1) Install / Update ASSella
  2) Uninstall ASSella (+ restore ACCELA if backup exists)
  3) Install / Run Headcrab
  q) Quit

Install flow: after installing ASSella, if Headcrab is not detected the script offers to run it immediately.
Headcrab flow: after running Headcrab, if ASSella is not installed the script offers to install it immediately.
Uninstall flow: removes ASSella, removes the ACCELA.AppImage symlink, reverts the desktop shortcut, and restores the original ACCELA backup if one exists.

### Settings — Headcrab Integration (Linux)

A new Headcrab section appears in Settings > Tools (Linux only).

- ASSella auto-detects whether Headcrab is installed by checking ~/.headcrab/ and ~/.local/share/applications/headcrab.desktop
- Status label shows green if installed, red if not detected
- Button label reads "Install Headcrab" or "Run Headcrab Again" depending on detection result
- Clicking confirms with a dialog, then opens a terminal running: curl -fsSL headcrab.pages.dev | bash

### Settings — ASSella Tab Uninstall Button (Linux)

An Uninstall ASSella button has been added at the bottom of the ASSella settings tab.

- Step 1: Confirms the uninstall action
- Step 2: If a backup (ACCELA.AppImage.bak) is found, asks whether to restore the original ACCELA
- Proceeds in one pass and reverts the desktop shortcut name back to ACCELA

---

## ASSella v1.8f — Changes from v1.8e

### Fake AppID Database Integration (Highly Experimental)

A new toggle in Settings > ASSella: "Fake AppID Database Integration".

- When enabled, ASSella merges a bundled curated list of games that support online play via Spacewar (FakeAppIds) into your SLSsteam config.yaml on every boot
- When disabled, any merged entries are cleanly removed, leaving user-configured entries untouched
- A config.yaml.bak backup is taken before any changes are made
- Marked highly experimental as SLSsteam config.yaml is sensitive to formatting errors

### Post-Download Status Fix

After downloading a game update, the game's library status now correctly updates to "Up to date" instead of remaining stuck on "Checking for update". The update status cache is also cleared for the game after a successful download so future checks work correctly.

### Multi-Select Depot UX Overhaul

The depot selection screen for games with multiple depots has been redesigned to be cleaner and less cluttered. Smart Selection remembers your depot choices per-game and automatically reuses them on future updates, only prompting again when a new depot is added since your last choice.

### Flat-Text Pause and Stop Controls

The Pause/Resume and Stop buttons below the download progress bar are now styled as flat clickable text to match the rest of the tool's UI, replacing the previously out-of-place button style.

---

Install or update ASSella:

  curl -fsSL https://raw.githubusercontent.com/niwia/ASSella/beta/install.sh | bash
