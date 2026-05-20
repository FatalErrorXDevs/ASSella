# ASSella

**ASSella** is a personal fork of [ACCELA](https://github.com/TachibanaLabs/ACCELA) — a Steam game downloader / launcher for Linux & Steam Deck — with custom theming and bundled integrations.

![ASSella Logo](./src/res/logo/accela.png)

## What's different from upstream ACCELA

| Feature | Status |
|---|---|
| **ASSella branding** in UI (title bar, dialogs) | ✅ |
| **Orange theme** (`#c36200` accent, `#1f1f1f` background) as default | ✅ |
| **Workshop Downloader** bundled (`workshop_downloader_linux`) | ✅ |
| **Steamless AIO** bundled (`steamless-aio.sh`) | ✅ |
| **SLSsteam** emulator integration | ✅ |
| Version `20260512+ASSella-1.0` | ✅ |

## Installation (Steam Deck / Linux)

1. Download `ASSella.AppImage` from the [Releases](../../releases) page
2. Make it executable:
   ```bash
   chmod +x ASSella.AppImage
   ```
3. Run it:
   ```bash
   ./ASSella.AppImage
   ```
4. (Optional) Copy `config.example.conf` to `~/.config/Tachibana Labs/ACCELA.conf` and fill in your API keys

## Configuration

Copy `config.example.conf` to `~/.config/Tachibana Labs/ACCELA.conf`.

The example file contains **only the styling** — you'll need to add your own API keys:
- `morrenus_api_key` — from [hubcapmanifest.com](https://hubcapmanifest.com)
- `sgdb_api_key` — from [SteamGridDB](https://www.steamgriddb.com)
- `steam_web_api_key` — from [Steam Web API](https://steamcommunity.com/dev/apikey)

## Building from source

```bash
git clone git@github.com:niwia/ASSella.git
cd ASSella
# Install dependencies
cd src && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Run
python3 src/main.py
```

## Credits

- Upstream: **ACCELA** by Tachibana Labs
- **SLSteam** — Steam DRM emulation library
- **Steamless** — SteamStub DRM unpacker
- **Workshop Downloader** — mod downloader by hubcap
- Fork by **niwia**

---

*ＧｏＤ_Ｉｓ_ｉＮ_ｔＨｅ_ＷｉＲｅＤ*
