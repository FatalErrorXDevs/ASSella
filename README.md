# ASSella

ASSella is a personal fork of ACCELA — a Steam game downloader and launcher for Linux and Steam Deck — bundling quality-of-life improvements, extra tools, and backend fixes on top of the original.

![ASSella Banner](./assela_banner_v2.png)

---

## Installation

Install or update ASSella with a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/niwia/ASSella/beta/install.sh | bash
```

The installer presents a menu with the following options:

- Install / Update ASSella
- Uninstall ASSella (restores original ACCELA if a backup is present)
- Install / Run Headcrab (installs the tools required for ASSella to work)

On first install, the script backs up your existing ACCELA.AppImage, downloads ASSella, creates a compatibility symlink, and patches the desktop shortcut.

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

- **Fake AppID Database Integration (Highly Experimental)** — toggle in Settings > ASSella. Merges a curated list of games supporting online play via Spacewar (FakeAppIds / 480 mapping) into your SLSsteam config.yaml on every boot. Disabled by default. Takes a config.yaml.bak backup before making any changes.
- **Steam Update Blocking status** — the home screen shows whether Steam auto-updates are blocked via steam.cfg (BootStrapperInhibitAll / BootStrapperForceSelfUpdate).

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
- Uninstall ASSella button — confirms the action, optionally restores the original ACCELA backup, and reverts the desktop shortcut

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
