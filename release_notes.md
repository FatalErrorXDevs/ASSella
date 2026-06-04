## What's new in ASSella v1.8g

### 🛠 Tools Tab — Headcrab Integration
- **Auto-detection**: ASSella now detects whether Headcrab is installed by checking `~/.headcrab/` and `~/.local/share/applications/headcrab.desktop`
- Status shown in Settings → Tools: green ✔ if installed, red ✘ if not
- **Install Headcrab** button (or **Run Headcrab Again** if already installed) — opens a terminal and runs the Headcrab setup script

### 🗂 Tools Tab — ASSella Manager
- **Uninstall ASSella**: removes `ASSella.AppImage`, removes the `ACCELA.AppImage` symlink, and reverts the desktop shortcut name back to ACCELA
- **Restore Original ACCELA**: restores `ACCELA.AppImage.bak` (the original ACCELA that was backed up at install time) and removes ASSella — only shown if the backup exists

### 📦 Installer Script — Interactive Menu
The `install.sh` is now a fully interactive menu-driven installer:
```
  1) Install / Update ASSella
  2) Uninstall ASSella (+ restore ACCELA if backup exists)
  3) Install / Run Headcrab
  q) Quit
```
- Option 1 (Install): after installing, offers to run Headcrab immediately if not detected
- Option 3 (Headcrab): after running, offers to install ASSella immediately if not already installed
- Uninstall automatically restores the original ACCELA backup if one exists

---

## What was new in ASSella v1.8f

### 🧬 Fake AppID Database Integration *(Experimental)*
- New toggle in Settings → ASSella: **Fake AppID Database Integration**
- Merges a curated list of games that support online play via Spacewar (FakeAppIds) into your SLSsteam `config.yaml`
- Automatic merge on every boot when enabled; clean removal when disabled
- Marked experimental — takes a `config.yaml.bak` backup before any changes

### ✅ Post-Download Status Fix
- After downloading a game update, the game's status now correctly updates to "Up to date" instead of showing "Checking for update" indefinitely

### 🎛 Multi-Select UX Overhaul
- Depot selection UI redesigned to be cleaner and less cluttered
- Smart Selection remembers your depot choices per-game and auto-selects them on future updates

### ⏸ Flat-Text Download Controls
- Pause/Resume and Stop controls below the download progress bar are now styled as flat clickable text, matching the rest of the tool's UI

---

## What was new in ASSella v1.8e

### ⬇️ Download Screen 2.0 (Beta)
- New download screen with redesigned layout (toggle in Settings → ASSella)
- Game name shown in the download queue instead of raw depot IDs

### 🐧 Linux DRM Detection
- If the downloading depots are Linux-only, DRM status now shows `No DRM (Linux)` instead of an error

### 🔇 Manifest Warning Removals
- Suppressed noisy manifest-related warnings in the log output

---

*Install or update ASSella:*
```bash
curl -fsSL https://raw.githubusercontent.com/niwia/ASSella/beta/install.sh | bash
```
