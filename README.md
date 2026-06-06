<p align="center">
  <img src="src/res/logo/icon.png" width="128" height="128" alt="ASSella Logo" />
</p>

# ASSella

ASSella is a personal fork of ACCELA — a Steam game downloader and launcher for Linux and Steam Deck — bundling quality-of-life improvements, extra tools, and backend fixes on top of the original.

![ASSella Banner](./assela_banner_v2.png)

---

## Installation (Stable/Beta)

Install or update ASSella with a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/niwia/ASSella/beta/install.sh | bash
```

The installer presents a menu with the following options:

- Install / Update ASSella
- Uninstall ASSella (restores original ACCELA if a backup is present)
- Install / Run Headcrab (installs the tools required for ASSella to work)

---

## Testing / Alpha (Remote Web UI & Headless Mode)

The **alpha** branch introduces remote WiFi control via a Web UI and a headless background mode designed for gaming mode. 

Install and manage the testing version:

```bash
curl -fsSL https://raw.githubusercontent.com/niwia/ASSella/alpha/install_testing.sh | bash
```

The testing installer installs an **extracted source + virtualenv** version to `~/.local/share/assella_testing` and provides options to:
- Install or update the testing files.
- Enable/Disable a **systemd user service** to run the headless server in the background automatically.
- Launch the testing GUI.
- Uninstall the testing files.

---

## What's New: Remote Web UI & Headless Mode

### 📱 Remote Web UI
Access and manage your game library from your phone or any device on the same WiFi network!
- **Library Grid**: View all installed games with name, update status, and Steam header images.
- **Search**: Fast local filter to search your games by name.
- **Queue Control**: Trigger updates for single games, check for library updates, or click **Update All** to download all pending updates.
- **Live Progress Monitor**: Docked at the bottom, showing the active download name, current stage (manifest check, downloading, removing DRM), speed, and queue count.

### ⚙️ Headless Mode
Run ASSella silently in the background without opening the desktop GUI window:
- Run via CLI: `/path/to/venv/bin/python src/main.py --headless --port 8765`
- Runs in the background (using Qt offscreen platform) so downloads and tools work flawlessly.
- Exposes Web UI on port `8765` (customizable with `--port`).
- Configurable as a systemd user service via the `install_testing.sh` menu.

---

## What ASSella adds over ACCELA

### Downloads

- **Smart Selection** — remembers which depots you chose for each game and automatically reuses them on future updates. Only prompts again when a new depot appears since your last selection.
- **Download Screen 2.0 (Beta)** — redesigned download screen with game names in the queue instead of raw depot IDs. Toggle in Settings > ASSella.
- **Pause / Stop controls** — flat clickable text controls below the download progress bar for pausing, resuming, and stopping the current download.
- **Post-download status fix** — after downloading a game update, the library status correctly reflects the updated state without requiring a manual recheck.
- **Linux DRM detection** — if all downloading depots are Linux-native, ASSella shows "No DRM (Linux)" in the post-download stats instead of an error.

### Library

- Installed Steam games are not shown in the ACCELA library view to reduce noise.

### SLSsteam / Config

- **Fake AppID Database Integration (Highly Experimental)** — toggle in Settings > ASSella. Merges a curated list of games supporting online play via fakeappids/spacewar into your SLSsteam config.yaml on every boot.
- **Steam Update Blocking status** — the home screen shows whether Steam auto-updates are blocked via steam.cfg.

### Home Screen

- Hubcap API stats shown on the home screen: daily usage, key expiry, and a reset indicator.
- Update All button to queue updates for all games with available updates.

### Tools (Settings > Tools)

- **Configure Achievements** — launch SLScheevo to set up achievement credentials.
- **Remove DRM** — run Steamless manually on a game executable.
- **Remove DRM (AIO)** — run Steamless-AIO manually.
- **Headcrab** — auto-detects whether Headcrab is installed. Shows install status and provides a button to install or re-run Headcrab from within ASSella.

### ASSella Settings Tab

- Smart Selection toggle
- Auto-fetch update manifests on boot toggle
- Download Screen 2.0 Beta toggle
- Fake AppID Database Integration toggle (experimental)
- **Enable Remote Web UI** — starts/stops the background Web UI server.
- Uninstall ASSella button — confirms the action, optionally restores the original ACCELA backup, and reverts the desktop shortcut.

### Bundled Tools

- Workshop Downloader (beta) — `workshop_downloader_linux`
- Steamless AIO (beta) — `steamless-aio.sh`

---

## Requirements

- Headcrab (recommended) — installs SLSteam and patches Steam for ASSella compatibility:
  `curl -fsSL headcrab.pages.dev | bash`
- SLSteam — required for depot downloading
- A valid Hubcap API key

---

*god is in the ass*
