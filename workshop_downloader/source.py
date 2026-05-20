import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os
import re
import subprocess
import threading
import requests
import configparser
import time

SETTINGS_FILE = "settings.ini"
KEYS_FILE = "workshop_keys.txt"
MANIFESTS_DIR = "manifests"
DDM_EXE = os.path.join("depotdownloader", "DepotDownloaderMod")

API_WORKSHOP = "https://hubcapmanifest.com/api/v1/generate/workshopmanifest/{wid}"

os.makedirs(MANIFESTS_DIR, exist_ok=True)


# ─── Settings ────────────────────────────────────────────────────────────────

def load_settings() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if os.path.exists(SETTINGS_FILE):
        cfg.read(SETTINGS_FILE, encoding="utf-8")
    if "general" not in cfg:
        cfg["general"] = {}
    if "steam" not in cfg:
        cfg["steam"] = {}
    return cfg


def save_settings(cfg: configparser.ConfigParser):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        cfg.write(f)


# ─── Steam path detection ─────────────────────────────────────────────────────

def detect_steamapps_path() -> str:
    home = os.path.expanduser("~")

    candidates = [
        os.path.join(home, ".steam", "steam"),
        os.path.join(home, ".steam", "root"),
        os.path.join(home, ".local", "share", "Steam"),
        os.path.join(home, "snap", "steam", "common", ".steam", "steam"),
        os.path.join(home, "snap", "steam", "common", ".local", "share", "Steam"),
        os.path.join(home, ".var", "app", "com.valvesoftware.Steam", ".steam", "steam"),
        os.path.join(home, ".var", "app", "com.valvesoftware.Steam", ".local", "share", "Steam"),
    ]

    for path in candidates:
        steamapps = os.path.join(path, "steamapps")
        if os.path.isdir(steamapps):
            return os.path.realpath(steamapps)

    return ""


# ─── Workshop IDs ─────────────────────────────────────────────────────────────

def extract_workshop_id(raw: str):
    raw = raw.strip()
    m = re.search(r"[?&]id=(\d+)", raw)
    if m:
        return m.group(1)
    if re.fullmatch(r"\d+", raw):
        return raw
    return None


def parse_workshop_ids(text: str):
    tokens = re.split(r"[\s,]+", text)
    ids = []
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        wid = extract_workshop_id(t)
        if wid:
            ids.append(wid)
    return list(dict.fromkeys(ids))


# ─── Manifest fetch ───────────────────────────────────────────────────────────

def fetch_manifest(wid: str, api_key: str, log_fn=None):
    try:
        r = requests.get(
            API_WORKSHOP.format(wid=wid),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        r.raise_for_status()
    except Exception as e:
        if log_fn:
            log_fn(f"  ✗ Manifest request failed: {e}")
        return None

    appid       = r.headers.get("X-App-Id")
    manifest_id = r.headers.get("X-Manifest-Id")
    depot_key   = r.headers.get("X-Depot-Key")

    if not appid or not manifest_id:
        if log_fn:
            log_fn("  ✗ Missing required headers in manifest response.")
        return None

    manifest_path = os.path.join(MANIFESTS_DIR, f"{appid}_{manifest_id}.manifest")
    with open(manifest_path, "wb") as f:
        f.write(r.content)

    return {
        "appid":         appid,
        "manifest_id":   manifest_id,
        "depot_key":     depot_key,
        "manifest_path": manifest_path,
    }


# ─── Depot keys ───────────────────────────────────────────────────────────────

def key_exists(appid: str) -> bool:
    if not os.path.exists(KEYS_FILE):
        return False
    with open(KEYS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith(f"{appid};"):
                return True
    return False


def save_key(appid: str, key: str):
    with open(KEYS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{appid};{key}\n")


# ─── ACF helpers ──────────────────────────────────────────────────────────────

def _get_dir_size(path: str) -> int:
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for fn in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, fn))
            except OSError:
                pass
    return total


def _parse_acf_block(text: str) -> dict:
    result = {}
    stack = [result]
    current_key = None
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        tokens = re.findall(r'"[^"]*"|\{|\}', s)
        for tok in tokens:
            if tok == "{":
                new = {}
                if current_key is not None:
                    stack[-1][current_key] = new
                    stack.append(new)
                    current_key = None
            elif tok == "}":
                if len(stack) > 1:
                    stack.pop()
            else:
                val = tok.strip('"')
                if current_key is None:
                    current_key = val
                else:
                    stack[-1][current_key] = val
                    current_key = None
    return result


def _write_acf(path: str, appid: str, items: dict):
    existing = {}
    root_meta = {}

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        parsed = _parse_acf_block(raw)
        aw = parsed.get("AppWorkshop", {})
        root_meta = {
            k: v for k, v in aw.items()
            if k not in ("WorkshopItemsInstalled", "WorkshopItemDetails",
                         "NeedsUpdate", "NeedsDownload")
            and isinstance(v, str)
        }
        installed = aw.get("WorkshopItemsInstalled", {})
        details   = aw.get("WorkshopItemDetails", {})
        for wid, data in installed.items():
            existing[wid] = {
                "size":         data.get("size", "0"),
                "timeupdated":  data.get("timeupdated", "0"),
                "manifest":     data.get("manifest", ""),
                "timetouched":  details.get(wid, {}).get("timetouched", "0"),
                "subscribedby": details.get(wid, {}).get("subscribedby", "0"),
            }

    for wid, info in items.items():
        existing[wid] = {
            "size":         str(info["size"]),
            "timeupdated":  str(info["timeupdated"]),
            "manifest":     str(info["manifest"]),
            "timetouched":  existing.get(wid, {}).get("timetouched", "0"),
            "subscribedby": existing.get(wid, {}).get("subscribedby", "0"),
        }

    def q(v):
        return f'"{v}"'

    lines = []
    lines.append('"AppWorkshop"')
    lines.append("{")
    lines.append(f'\t"appid"\t\t{q(appid)}')

    for k, v in root_meta.items():
        if k == "appid":
            continue
        lines.append(f'\t{q(k)}\t\t{q(v)}')

    lines.append('\t"NeedsUpdate"\t\t"0"')
    lines.append('\t"NeedsDownload"\t\t"0"')

    lines.append('\t"WorkshopItemsInstalled"')
    lines.append("\t{")
    for wid, d in existing.items():
        lines.append(f'\t\t{q(wid)}')
        lines.append("\t\t{")
        lines.append(f'\t\t\t"size"\t\t{q(d["size"])}')
        lines.append(f'\t\t\t"timeupdated"\t\t{q(d["timeupdated"])}')
        lines.append(f'\t\t\t"manifest"\t\t{q(d["manifest"])}')
        lines.append("\t\t}")
    lines.append("\t}")

    lines.append('\t"WorkshopItemDetails"')
    lines.append("\t{")
    for wid, d in existing.items():
        lines.append(f'\t\t{q(wid)}')
        lines.append("\t\t{")
        lines.append(f'\t\t\t"manifest"\t\t{q(d["manifest"])}')
        lines.append(f'\t\t\t"timeupdated"\t\t{q(d["timeupdated"])}')
        lines.append(f'\t\t\t"timetouched"\t\t{q(d["timetouched"])}')
        lines.append(f'\t\t\t"subscribedby"\t\t{q(d["subscribedby"])}')
        lines.append(f'\t\t\t"latest_timeupdated"\t\t{q(d["timeupdated"])}')
        lines.append(f'\t\t\t"latest_manifest"\t\t{q(d["manifest"])}')
        lines.append("\t\t}")
    lines.append("\t}")
    lines.append("}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ─── Steam integration ────────────────────────────────────────────────────────

def apply_steam_integration(
    appid: str,
    wid: str,
    manifest_id: str,
    mod_dir: str,
    steamapps_path: str,
    log_fn,
):
    acf_path = os.path.join(steamapps_path, "workshop", f"appworkshop_{appid}.acf")
    size = _get_dir_size(mod_dir)
    now  = int(time.time())
    try:
        _write_acf(acf_path, appid, {wid: {
            "size":        size,
            "timeupdated": now,
            "manifest":    manifest_id,
        }})
        log_fn(f"  ✓ ACF updated → {acf_path}")
    except Exception as e:
        log_fn(f"  ✗ Failed to update ACF: {e}")


# ─── Download ─────────────────────────────────────────────────────────────────

def download_items(wids, api_key, max_downloads, cellid,
                   steam_integration, steamapps_path, log_fn):
    if not os.path.exists(DDM_EXE):
        log_fn(f"  ✗ Executable not found: {DDM_EXE}")
        log_fn("  All tasks finished.")
        return

    log_fn(f"  ✓ Using: {DDM_EXE}")

    for wid in wids:
        log_fn(f"\n{'─' * 52}")
        log_fn(f"  Workshop ID : {wid}")

        log_fn("  → Fetching manifest...")
        info = fetch_manifest(wid, api_key, log_fn=log_fn)
        if not info:
            log_fn("  ✗ Could not fetch manifest. Skipping.")
            continue

        appid         = info["appid"]
        manifest_id   = info["manifest_id"]
        depot_key     = info["depot_key"]
        manifest_path = info["manifest_path"]

        log_fn(f"  ✓ App ID     : {appid}")
        log_fn(f"  ✓ Manifest ID: {manifest_id}")
        log_fn(f"  ✓ Manifest   : {manifest_path}")

        if not depot_key:
            log_fn("  ✗ No depot key in response. Skipping.")
            continue

        if not key_exists(appid):
            save_key(appid, depot_key)
            log_fn(f"  ✓ Key saved  : {appid};{depot_key[:10]}…")
        else:
            log_fn(f"  ✓ Depot key for App ID {appid} already cached.")

        if steam_integration and steamapps_path:
            out_dir = os.path.join(steamapps_path, "workshop", "content", appid, wid)
        else:
            out_dir = os.path.join("mods", appid, wid)

        cmd = [
            DDM_EXE,
            "-app", appid,
            "-ugc", wid,
            "-manifestfile", manifest_path,
            "-depotkeys", KEYS_FILE,
            "-dir", out_dir,
            "-max-downloads", str(max_downloads),
        ]
        if cellid is not None:
            cmd += ["-cellid", str(cellid)]

        log_fn(f"  → Running    : {' '.join(cmd)}")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for line in proc.stdout:
                log_fn(f"    {line.rstrip()}")
            proc.wait()
            if proc.returncode == 0:
                log_fn(f"  ✓ Download complete → {out_dir}")
            else:
                log_fn(f"  ✗ DepotDownloader exited with code {proc.returncode}.")
                continue
        except Exception as e:
            log_fn(f"  ✗ Failed to launch DepotDownloader: {e}")
            continue

        if steam_integration and steamapps_path:
            log_fn("  → Applying Steam integration...")
            apply_steam_integration(
                appid, wid, manifest_id,
                out_dir, steamapps_path, log_fn,
            )

    log_fn(f"\n{'─' * 52}")
    log_fn("  All tasks finished.")


# ─── UI ───────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Workshop Downloader")
        self.minsize(740, 620)
        self.resizable(True, True)

        self._cfg = load_settings()
        self._key_visible = False
        self._build_ui()
        self._load_from_settings()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # API key
        frm_api = ttk.LabelFrame(self, text=" API Key  (manifest.morrenus.xyz) ")
        frm_api.pack(fill="x", **pad)

        self.var_api_key = tk.StringVar()
        self._api_entry = ttk.Entry(
            frm_api, textvariable=self.var_api_key, show="●", width=58)
        self._api_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=6)
        ttk.Button(
            frm_api, text="Show", width=5, command=self._toggle_key_visibility,
        ).pack(side="left", padx=(2, 8), pady=6)

        # Workshop IDs
        frm_ids = ttk.LabelFrame(
            self, text=" Workshop IDs or Steam URLs  (one per line, or comma-separated) ")
        frm_ids.pack(fill="both", expand=True, **pad)
        self.txt_ids = scrolledtext.ScrolledText(frm_ids, height=7, wrap="word")
        self.txt_ids.pack(fill="both", expand=True, padx=8, pady=6)

        # Options row
        frm_opts = ttk.Frame(self)
        frm_opts.pack(fill="x", **pad)

        ttk.Label(frm_opts, text="Max downloads:").pack(side="left")
        self.var_max_downloads = tk.IntVar(value=8)
        ttk.Spinbox(
            frm_opts, from_=1, to=1024,
            textvariable=self.var_max_downloads, width=6,
        ).pack(side="left", padx=(4, 0))

        ttk.Label(frm_opts, text="Cell ID:").pack(side="left", padx=(12, 0))
        self.var_cellid = tk.StringVar(value="")
        ttk.Entry(frm_opts, textvariable=self.var_cellid, width=6).pack(
            side="left", padx=(4, 0))

        # Steam integration
        frm_steam = ttk.LabelFrame(self, text=" Steam Integration ")
        frm_steam.pack(fill="x", **pad)

        self.var_steam_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frm_steam, text="Enable", variable=self.var_steam_enabled,
            command=self._on_steam_toggle,
        ).grid(row=0, column=0, padx=(8, 12), pady=6)

        ttk.Label(frm_steam, text="Steamapps:").grid(
            row=0, column=1, sticky="w", pady=6)
        self.var_steamapps_path = tk.StringVar()
        self._entry_steamapps = ttk.Entry(
            frm_steam, textvariable=self.var_steamapps_path, width=52)
        self._entry_steamapps.grid(
            row=0, column=2, padx=(4, 4), pady=6, sticky="ew")
        self._btn_steamapps = ttk.Button(
            frm_steam, text="…", width=3, command=self._browse_steamapps)
        self._btn_steamapps.grid(row=0, column=3, padx=(0, 8), pady=6)

        frm_steam.columnconfigure(2, weight=1)
        self._on_steam_toggle()

        # Buttons row
        frm_bar = ttk.Frame(self)
        frm_bar.pack(fill="x", **pad)

        self.btn_download = ttk.Button(
            frm_bar, text="⬇  Download", width=14, command=self._start_download)
        self.btn_download.pack(side="left", padx=(0, 6))

        ttk.Button(
            frm_bar, text="Clear Log", width=10, command=self._clear_log,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            frm_bar, text="💾  Save Settings", width=16, command=self._save_settings_btn,
        ).pack(side="left")

        self.lbl_status = ttk.Label(frm_bar, text="")
        self.lbl_status.pack(side="left", padx=14)

        # Log
        frm_log = ttk.LabelFrame(self, text=" Log ")
        frm_log.pack(fill="both", expand=True, **pad)
        self.txt_log = scrolledtext.ScrolledText(
            frm_log, height=12, state="disabled", wrap="word",
            background="#1e1e1e", foreground="#d4d4d4",
            insertbackground="#d4d4d4", font=("Consolas", 9),
        )
        self.txt_log.pack(fill="both", expand=True, padx=8, pady=6)
        self.txt_log.tag_config("ok",    foreground="#4ec9b0")
        self.txt_log.tag_config("err",   foreground="#f44747")
        self.txt_log.tag_config("info",  foreground="#9cdcfe")
        self.txt_log.tag_config("sep",   foreground="#555555")
        self.txt_log.tag_config("plain", foreground="#d4d4d4")

    # ── settings ──────────────────────────────────────────────────────────

    def _load_from_settings(self):
        cfg = self._cfg
        self.var_api_key.set(cfg["general"].get("api_key", ""))

        enabled = cfg["steam"].get("enabled", "false").lower() == "true"
        self.var_steam_enabled.set(enabled)

        steamapps = cfg["steam"].get("steamapps_path", "")
        if not steamapps:
            steamapps = detect_steamapps_path()
        self.var_steamapps_path.set(steamapps)

        self._on_steam_toggle()

    def _persist_settings(self):
        cfg = self._cfg
        cfg["general"]["api_key"]      = self.var_api_key.get().strip()
        cfg["steam"]["enabled"]        = str(self.var_steam_enabled.get())
        cfg["steam"]["steamapps_path"] = self.var_steamapps_path.get().strip()
        save_settings(cfg)

    def _save_settings_btn(self):
        self._persist_settings()
        self._set_status("✓ Settings saved.")

    def _toggle_key_visibility(self):
        self._key_visible = not self._key_visible
        self._api_entry.config(show="" if self._key_visible else "●")

    def _on_steam_toggle(self):
        state = "normal" if self.var_steam_enabled.get() else "disabled"
        self._entry_steamapps.config(state=state)
        self._btn_steamapps.config(state=state)

    def _browse_steamapps(self):
        initial = self.var_steamapps_path.get() or os.path.expanduser("~")
        path = filedialog.askdirectory(title="Select steamapps folder", initialdir=initial)
        if path:
            self.var_steamapps_path.set(path)

    # ── log ───────────────────────────────────────────────────────────────

    def _resolve_tag(self, msg: str):
        s = msg.strip()
        if s.startswith("✓"):             return "ok"
        if s.startswith("✗"):             return "err"
        if s.startswith("→"):             return "info"
        if not s or set(s) <= {"─", " "}: return "sep"
        return "plain"

    def _log(self, msg: str):
        tag = self._resolve_tag(msg)
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", msg + "\n", tag)
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def _clear_log(self):
        self.txt_log.config(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.config(state="disabled")

    def _set_status(self, text: str):
        self.lbl_status.config(text=text)

    def _start_download(self):
        api_key = self.var_api_key.get().strip()
        if not api_key:
            messagebox.showwarning("No API Key",
                                   "Please enter your API key before downloading.")
            return

        raw = self.txt_ids.get("1.0", "end").strip()
        if not raw:
            messagebox.showwarning("No IDs",
                                   "Please enter at least one Workshop ID or URL.")
            return

        wids = parse_workshop_ids(raw)
        if not wids:
            messagebox.showwarning("No Valid IDs",
                                   "Could not parse any Workshop IDs from the input.")
            return

        try:
            max_downloads = int(self.var_max_downloads.get())
            if max_downloads < 1:
                raise ValueError
        except (ValueError, tk.TclError):
            max_downloads = 8
            self.var_max_downloads.set(8)

        cellid_raw = self.var_cellid.get().strip()
        if cellid_raw:
            if not cellid_raw.isdigit():
                messagebox.showwarning("Invalid Value", "Cell ID must be a number.")
                return
            cellid = int(cellid_raw)
        else:
            cellid = None

        steam_integration = self.var_steam_enabled.get()
        steamapps_path    = self.var_steamapps_path.get().strip()

        if steam_integration and not steamapps_path:
            messagebox.showwarning(
                "Steam Integration",
                "Steamapps path is empty. Please set it or disable Steam Integration.",
            )
            return

        self._persist_settings()

        self._log(f"Queued {len(wids)} item(s): {', '.join(wids)}")
        self._log(f"  → Max downloads : {max_downloads}")
        if cellid is not None:
            self._log(f"  → Cell ID       : {cellid}")
        if steam_integration:
            self._log(f"  → Steamapps     : {steamapps_path}")

        self.btn_download.config(state="disabled")
        self._set_status("⏳ Downloading…")

        def worker():
            download_items(
                wids, api_key, max_downloads, cellid,
                steam_integration, steamapps_path,
                log_fn=lambda m: self.after(0, self._log, m),
            )
            self.after(0, self._on_done)

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self):
        self.btn_download.config(state="normal")
        self._set_status("✅ Done.")


if __name__ == "__main__":
    app = App()
    app.mainloop()

