# ASSella — Advanced Steam Integration & Depot Manager

[![Version](https://img.shields.io/badge/version-v2.5.6--beta-blue.svg)](https://github.com/niwia/ASSella/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Steam%20Deck-orange.svg)]()

ASSella is a powerful, modern GUI and CLI manager for downloading, managing, and integrating Steam game depots, manifests, and licenses natively with Steam and SLSsteam on Linux desktop environments and Steam Deck.

---

## 🚀 What's New in v2.5.6-beta

### 1. Native SLSsteam ACF Manifest Integration (Experimental)
ASSella now offers native `.acf` manifest delegation powered by SLSsteam's IPC API (`/tmp/SLSsteam.API`):
- **100% Native Steam Manifests**: For standard installations, ASSella delegates `.acf` manifest creation directly to Steam client. Steam detects downloaded game files, reads depot manifests in `depotcache/`, and natively writes `appmanifest_<appid>.acf`.
- **Instant Playability**: Games transition directly to **Ready to Play / PLAY (Green)** in Steam client UI without requiring Steam restarts.
- **Native Uninstallation**: Standard uninstallation sends `uninstall|<appid>` to `/tmp/SLSsteam.API`, removes the entry from `config.yaml` in-place, and deletes game files. Steam client natively unregisters the title and removes `appmanifest_<appid>.acf`.
- **Memory Propagation Pause**: Automatically polls `~/.SLSsteam.log` for `AppLicensesChanged` / `Unlocked` events and inserts a 1.5-second memory propagation delay before firing install commands.

### 2. Pre-Cleanup Depotcache Manifest Preservation
- Automatically copies binary `.manifest` depot files into Steam's central `~/.local/share/Steam/depotcache/` *before* temporary directory cleanup runs.
- Guarantees Steam client can verify local game files and create/update manifests cleanly.

### 3. In-Place SLS Config Modifications (`IN_CLOSE_WRITE`)
- Modified `add_additional_app` and `remove_additional_app` to edit `~/.config/SLSsteam/config.yaml` in-place.
- Preserves the file inode, ensuring SLSsteam's Linux `inotify` watcher receives `IN_CLOSE_WRITE` events and reloads configuration instantly.

### 4. PICS-Native Fallback & Pinned Build Preservation
- Upgraded ASSella's fallback `.acf` generator to construct **100% Bit-for-Bit PICS-Native ACF** manifests:
  - **Active `LastOwner`**: Dynamically extracts the active user's 64-bit SteamID from `loginusers.vdf`.
  - **Version Locking**: Correctly sets `TargetBuildID` and pinned depot manifest GIDs for older/rollback builds, preventing Steam from forcing unwanted background auto-updates.

### 5. ISP Bypass for Hubcap API
- Added optional ISP Bypass that routes Hubcap API requests through Google/Cloudflare DNS (1.1.1.1/8.8.8.8) or background Tor fallback to bypass local ISP DNS censorship without affecting game file download speeds.

### 6. Universal Linux Path Support
- Replaced hardcoded path assumptions with dynamic `Path.home()` and `os.path.expanduser("~")` across all modules for seamless operation on standard Linux desktops, SteamOS, and custom library paths.

---

## 🛠️ Installation & One-Liner

Run the one-liner installer in your terminal to fetch and set up the latest ASSella release:

```bash
curl -fsSL https://raw.githubusercontent.com/niwia/ASSella/beta/install.sh | bash
```

### Manual AppImage Execution
```bash
chmod +x ASSella.AppImage
./ASSella.AppImage
```

---

## 📖 Architecture: How Native ACF Integration Works

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. DOWNLOAD & PREPARE                                                  │
│    ASSella downloads game content to steamapps/common/{installdir}     │
│    Depot manifests are saved to /tmp/mistwalker_manifests/             │
└──────────────────┬─────────────────────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. DEPOTCACHE PRESERVATION                                             │
│    Manifests copied → ~/.local/share/Steam/depotcache/                 │
└──────────────────┬─────────────────────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. IN-PLACE CONFIG & LOG WATCHING                                      │
│    AppID added to AdditionalApps in config.yaml (IN_CLOSE_WRITE)       │
│    ASSella waits for "AppLicensesChanged" event in ~/.SLSsteam.log     │
└──────────────────┬─────────────────────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 4. SLS API TRIGGER & NATIVE CREATION                                   │
│    "install|{appid}|{index}" sent to /tmp/SLSsteam.API                 │
│    Steam client verifies files and NATIVELY writes appmanifest_.acf    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Configuration & Settings

You can toggle experimental features anytime in **Settings -> Experimental**:
- **Let SLS handle ACF (Experimental)**: Toggle between native Steam `.acf` creation and ASSella fallback manifest generation.
- **Enable ISP Bypass (Hubcap API)**: Bypass ISP censorship for metadata fetching.

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for details.
