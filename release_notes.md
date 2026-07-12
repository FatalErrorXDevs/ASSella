# Release Notes - ASSella v2.2.2-rc1

Welcome to v2.2.2-rc1 in the preview/beta branch! This release introduces the new DLC-only installation mode, image caching upgrades, style settings cleanups, and visual/UX fixes.

### 📦 Features

#### 🔌 DLC Only Mode
* **Partial Depot Installations:** Easily install and update only the DLC depots of games you already own on Steam (e.g. soundtracks, extra content packs).
* **Flexible Toggles:** Enable it during download from the depot selection screen via the **DLC Only** toggle button, or opt-in later via the **DLC Only Mode** switch in the game details preferences card.
* **Smart Update Checking:** When enabled, ASSella skips checking the main game manifest. It queries Steam's API only for your chosen DLC depots and compares them with local versions. You will only get update notifications when the DLC files themselves actually change!
* **Bypasses Steamless:** Automatically skips DRM processing for DLC-only installations, avoiding modifying base executables.

#### 🎨 Interface & Style tab Redesign
* **Compact Settings Layout:** Consolidated Theme Colors and Font settings into a single clean Grid layout. Swatches are now styled color pills.
* **Nerd Mode Removed:** The setting is now set to False by default, permanently keeping the simplified, modern UI active.
* **Origins Easter Egg:** Added a new Display Setting checkbox labeled **"Remember your origins"**. Enabling it triggers a quick flash/fade transition and runs the watermarked Lain GIF subtly behind all settings controls.
* **Removed Legacy GIF/Audio Clutter:** Completely deleted legacy Accela GIF folders and verified absolute silence on boot/exit.

#### 🖼️ Raw Image Caching & Robust Fallbacks
* **Zero Quality Loss:** Capsule and Hero images are cached in their original, uncompressed formats without compression artifacts.
* **Smart Disk Bounds:** Set a strict 100MB rolling cache limit, automatically cleaning up the oldest cached images. The cache is deleted automatically if ASSella is uninstalled.
* **Async URL Fallback Sequence:** The image fetcher sequentially queries fallback URLs (Header, Library Capsule, Hero, Capsule base formats) asynchronously, resolving blank covers for games that don't have default headers.

### 🐛 Bug Fixes
* **Removed Suffixes:** Fully stripped the redundant `[ACCELA]` display tag suffix from the game library.
* **Past Downloads:** Correctly formats the history list to append `[DLC MODE]` when a DLC-only job finishes.
* **Dialog Branding:** Fixed QApplication titlebar headers and download status progress bars to reflect the `ASSella` name instead of legacy values.
