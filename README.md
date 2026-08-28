# ASSella

ASSella is a fork of ACCELA designed for Linux and Steam Deck.

ASSella 1.0 (Main Branch) is built on top of standard ACCELA with strictly 3 targeted changes:
1. **Workshop Downloader (beta) bundled** (`workshop_downloader_linux`).
2. **Steamless AIO (beta) bundled** (`steamless-aio.sh`).
3. **Library View Filtering**: Removed showing installed Steam games in the ACCELA library view so only games downloaded via ACCELA/ASSella are displayed.

> **Note:** You can always uninstall ASSella or revert back to standard ACCELA at any time using the installer menu.

---

## 📦 Beta Branch Installation (Feature-Rich Build)

For advanced features including Import Mode (user-provided LUA/manifests), Smart Depot Selection, Version Rollbacks, SLS Denuvo management, and thread-safe library scanning, install the **Beta Branch**:

```bash
curl -fsSL https://raw.githubusercontent.com/FatalErrorXDevs/ASSella/beta/install.sh | bash
```

> **⚠️ Warning:** The Beta branch is an active work-in-progress with approximately **90% stability**. If you encounter any unexpected issues, you can easily switch back to the stable ASSella 1.0 main branch or original ACCELA using the installer options.

---

## 📋 Requirements
* **Headcrab (SLSsteam)**: Required to intercept and download depots:
  `curl -fsSL headcrab.pages.dev | bash`
* **.NET 9 Runtime**: Automatically installed if missing, required for Steamless and DepotDownloader tools.
* **Hubcap API Key**: Required for Hubcap fallback/history queries; complete local Lua imports can use native SLSsteam/WUDRM instead.

## Manifest sources

Manifest acquisition is provider-based. Local `.lua` files are parsed first;
when they contain a manifest GID and depot key for every depot, ASSella can
configure SLSsteam/WUDRM to retrieve the manifest directly from Steam without
creating an intermediate ZIP. WUDRM's manifest-request lookup retries empty
successful responses. If native inputs are unavailable or incomplete, the
existing Hubcap provider remains the fallback and its binary endpoints retry
HTTP 200 responses that contain no body before failing.

Provider metadata is cached under `manifest_sources/<provider>/` with the
provider name and branch included, so additional sources can be added without
changing download-task code.

---

## ❄️ NixOS Compatibility

NixOS does not use standard `/lib64/ld-linux-x86-64.so.2` dynamic linkers, which causes generic Linux AppImages to display `stub-ld` or missing `libzstd.so.1` warnings. NixOS users can run ASSella using any of the following methods:

### 1. Using `steam-run` (Recommended — Includes libzstd.so.1 & Graphics Drivers)
```bash
nix-shell -p steam-run --run "steam-run ~/.local/share/ACCELA/ASSella.AppImage"
```

### 2. Using `appimage-run` with `zstd`
```bash
nix-shell -p appimage-run zstd --run "appimage-run ~/.local/share/ACCELA/ASSella.AppImage"
```

### 3. Global Fix (`nix-ld`)
Add `programs.nix-ld.enable = true;` and `zstd` to `/etc/nixos/configuration.nix` and rebuild.

---

*god is in the ass*
