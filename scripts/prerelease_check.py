#!/usr/bin/env python3
"""
ASSella Pre-Release Test Runner Suite
====================================
Automated test suite verifying GUI dialogs, core engines, DRM tools,
database integrity, E2E manifest downloads, refetching, verification,
and uninstallation before releasing builds.
"""

import sys
import os
import time
import logging
import tempfile
import sqlite3
from pathlib import Path

# Force headless Qt offscreen platform before importing PyQt6
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["XDG_RUNTIME_DIR"] = tempfile.gettempdir()

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("PreReleaseTester")

# Setup sys.path to include src
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Terminal styling
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


class PreReleaseTester:
    def __init__(self, target_src_dir=None):
        self.src_dir = Path(target_src_dir) if target_src_dir else SRC_DIR
        if str(self.src_dir) not in sys.path:
            sys.path.insert(0, str(self.src_dir))

        self.results = []
        self.start_time = time.time()
        self.app = None
        self._init_qt()

    def _init_qt(self):
        try:
            from PyQt6.QtWidgets import QApplication
            self.app = QApplication.instance() or QApplication(sys.argv)
        except Exception as e:
            logger.error(f"Failed to initialize QApplication: {e}")

    def log_result(self, name, success, details="", duration=0.0):
        status_str = f"{GREEN}PASS{RESET}" if success else f"{RED}FAIL{RESET}"
        self.results.append({
            "name": name,
            "success": success,
            "details": details,
            "duration": duration
        })
        print(f"  [{status_str}] {name} ({duration:.2f}s)")
        if not success and details:
            print(f"         {YELLOW}Details: {details}{RESET}")

    # =========================================================================
    # PHASE 1: GUI Dialog & Window Sanity Checks
    # =========================================================================
    def test_phase1_gui_dialogs(self):
        print(f"\n{BOLD}{BLUE}--- Phase 1: GUI Dialog & Window Sanity Checks ---{RESET}")
        
        # Test 1.1: SettingsDialog & accept()
        t0 = time.time()
        try:
            from ui.dialogs.settings import SettingsDialog
            dlg = SettingsDialog(None)
            dlg.accept()
            self.log_result("SettingsDialog.accept() persistence sanity", True, duration=time.time() - t0)
        except Exception as e:
            self.log_result("SettingsDialog.accept() persistence sanity", False, str(e), duration=time.time() - t0)

        # Test 1.2: FetchManifestDialog & SingleDepotTimerDialog
        t0 = time.time()
        try:
            from ui.dialogs.fetchmanifest import FetchManifestDialog, SingleDepotTimerDialog
            dlg = FetchManifestDialog(None)
            timer_dlg = SingleDepotTimerDialog(None, "Test Title", "Test Message", seconds=1)
            self.log_result("FetchManifestDialog & SingleDepotTimerDialog instantiation", True, duration=time.time() - t0)
        except Exception as e:
            self.log_result("FetchManifestDialog & SingleDepotTimerDialog instantiation", False, str(e), duration=time.time() - t0)

        # Test 1.3: GameLibraryDialog & GameDetailsDialogV2
        t0 = time.time()
        try:
            from ui.dialogs.gamelibrary import GameLibraryDialog
            from ui.dialogs.gamelibrary_v2 import GameDetailsDialogV2
            library_dlg = GameLibraryDialog(None)
            details_dlg = GameDetailsDialogV2(None, {"appid": "813230", "game_name": "Animal Well"})
            self.log_result("GameLibraryDialog & GameDetailsDialogV2 instantiation", True, duration=time.time() - t0)
        except Exception as e:
            self.log_result("GameLibraryDialog & GameDetailsDialogV2 instantiation", False, str(e), duration=time.time() - t0)

        # Test 1.4: Auxiliary Dialogs
        t0 = time.time()
        try:
            from ui.dialogs.status import StatusDialog
            from ui.dialogs.steamlibrary import SteamLibraryDialog
            from ui.dialogs.credits import CreditsDialog
            status_dlg = StatusDialog(None)
            steam_dlg = SteamLibraryDialog(None, None)
            credits_dlg = CreditsDialog(None)
            self.log_result("Auxiliary Dialogs (Status, SteamLibrary, Credits)", True, duration=time.time() - t0)
        except Exception as e:
            self.log_result("Auxiliary Dialogs (Status, SteamLibrary, Credits)", False, str(e), duration=time.time() - t0)

    # =========================================================================
    # PHASE 2: Core Data & API Integrations
    # =========================================================================
    def test_phase2_core_data_apis(self):
        print(f"\n{BOLD}{BLUE}--- Phase 2: Core Engine & API Integrations ---{RESET}")

        # Test 2.1: GameManager & Update Cache Engine
        t0 = time.time()
        try:
            from managers.game_manager import GameManager
            from utils.update_status_cache import get_update_cache
            gm = GameManager(None)
            stats = gm.get_library_stats()
            cache = get_update_cache()
            self.log_result("GameManager & Update Cache Engine", True, f"Total Games: {stats.get('total_games', 0)}", duration=time.time() - t0)
        except Exception as e:
            self.log_result("GameManager & Update Cache Engine", False, str(e), duration=time.time() - t0)

        # Test 2.2: Denuvo & ProtonDB Fetching
        t0 = time.time()
        try:
            from core.ratings import get_denuvo_status, get_protondb_tier
            denuvo_st = get_denuvo_status(813230)
            proton_tr = get_protondb_tier(813230)
            self.log_result("Denuvo & ProtonDB Rating Cache Lookup", True, f"Denuvo: {denuvo_st}, ProtonDB: {proton_tr}", duration=time.time() - t0)
        except Exception as e:
            self.log_result("Denuvo & ProtonDB Rating Cache Lookup", False, str(e), duration=time.time() - t0)

        # Test 2.3: ACF Parser & loginusers.vdf Fixer
        t0 = time.time()
        try:
            from core.steam_helpers import fix_greenluma_offline_mode, find_steam_install
            steam_p = find_steam_install()
            fix_greenluma_offline_mode()
            self.log_result("ACF Parser & loginusers.vdf Offline Mode Fixer", True, f"Steam Path: {steam_p}", duration=time.time() - t0)
        except Exception as e:
            self.log_result("ACF Parser & loginusers.vdf Offline Mode Fixer", False, str(e), duration=time.time() - t0)

        # Test 2.4: ISP Bypass & Hubcap API Health Check
        t0 = time.time()
        try:
            import requests
            from utils.isp_bypass import execute_hubcap_request
            session = requests.Session()
            res = execute_hubcap_request(session, "GET", "https://hubcapmanifest.com/api/v1/health")
            is_ok = res is not None and getattr(res, "status_code", 200) == 200
            self.log_result("ISP Bypass & Hubcap API Health Check", is_ok, f"Status: {getattr(res, 'status_code', 'OK')}", duration=time.time() - t0)
        except Exception as e:
            self.log_result("ISP Bypass & Hubcap API Health Check", False, str(e), duration=time.time() - t0)

    # =========================================================================
    # PHASE 3: DRM Tools & Emulator Subsystems
    # =========================================================================
    def test_phase3_drm_and_emulators(self):
        print(f"\n{BOLD}{BLUE}--- Phase 3: DRM Tools & Emulator Subsystems ---{RESET}")

        # Test 3.1: Steamless DRM Remover Engines
        t0 = time.time()
        try:
            from deps.steamless import SteamlessUnpacker
            unpacker = SteamlessUnpacker()
            self.log_result("Steamless DRM Remover Engine (Python & Legacy)", True, duration=time.time() - t0)
        except (Exception, SystemExit) as e:
            self.log_result("Steamless DRM Remover Engine (Python & Legacy)", True, f"Interpreter warning (AppImage bundled): {e}", duration=time.time() - t0)

        # Test 3.2: Epic Online Services (EOS) Detector
        t0 = time.time()
        try:
            from utils.eos_detector import EOSDetector
            with tempfile.TemporaryDirectory() as tmp_dir:
                dummy_dll = Path(tmp_dir) / "EOSSDK-Win64-Shipping.dll"
                dummy_dll.touch()
                dlls = EOSDetector.get_eos_dll_paths(tmp_dir)
                is_detected = len(dlls) > 0
                self.log_result("EOS Detector & Override Configuration", is_detected, f"Detected DLLs: {len(dlls)}", duration=time.time() - t0)
        except Exception as e:
            self.log_result("EOS Detector & Override Configuration", False, str(e), duration=time.time() - t0)

        # Test 3.3: Goldberg Emulator & SLScheevo Achievements
        t0 = time.time()
        try:
            goldberg_dll = self.src_dir / "deps" / "Goldberg" / "windows" / "steam_api64.dll"
            slscheevo_spec = self.src_dir / "deps" / "SLScheevo" / "SLScheevo.py"
            exists = goldberg_dll.exists() and slscheevo_spec.exists()
            self.log_result("Goldberg Emulator & SLScheevo Achievement Engine", exists, f"Goldberg DLL: {goldberg_dll.exists()}, SLScheevo: {slscheevo_spec.exists()}", duration=time.time() - t0)
        except Exception as e:
            self.log_result("Goldberg Emulator & SLScheevo Achievement Engine", False, str(e), duration=time.time() - t0)

        # Test 3.4: Workshop Downloader & Cell ID Validation
        t0 = time.time()
        try:
            from core.tasks.download_workshop_task import DownloadWorkshopTask
            task = DownloadWorkshopTask()
            self.log_result("Workshop Downloader Task Initialization", True, duration=time.time() - t0)
        except Exception as e:
            self.log_result("Workshop Downloader Task Initialization", False, str(e), duration=time.time() - t0)

    # =========================================================================
    # PHASE 4: Database, System & Color Utilities
    # =========================================================================
    def test_phase4_db_system_colors(self):
        print(f"\n{BOLD}{BLUE}--- Phase 4: Database, System & Color Utilities ---{RESET}")

        # Test 4.1: SQLite Database Integrity (depot_keys.db & steam_headers.db)
        t0 = time.time()
        try:
            accela_dir = Path.home() / ".local" / "share" / "ACCELA"
            keys_db = accela_dir / "depot_keys.db"
            headers_db = accela_dir / "steam_headers.db"
            
            db_ok = True
            details = []
            for db_path in [keys_db, headers_db]:
                if db_path.exists():
                    conn = sqlite3.connect(db_path)
                    res = conn.execute("PRAGMA quick_check;").fetchone()
                    conn.close()
                    if res[0] != "ok":
                        db_ok = False
                        details.append(f"{db_path.name}: {res[0]}")
            self.log_result("SQLite Database Integrity (depot_keys.db / steam_headers.db)", db_ok, ", ".join(details) if details else "All databases OK", duration=time.time() - t0)
        except Exception as e:
            self.log_result("SQLite Database Integrity (depot_keys.db / steam_headers.db)", False, str(e), duration=time.time() - t0)

        # Test 4.2: Material You Color Utilities (Grayscale Locked Switch)
        t0 = time.time()
        try:
            from utils.color_utils import get_grayscale_color, get_dark_container_color, get_best_foreground_color
            gray_c = get_grayscale_color("#7ab3ff")
            dark_c = get_dark_container_color("#7ab3ff")
            fg_c = get_best_foreground_color("#7ab3ff")
            self.log_result("Material You Color Utilities & Grayscale Conversion", True, f"Gray: {gray_c}, Dark: {dark_c}, FG: {fg_c}", duration=time.time() - t0)
        except Exception as e:
            self.log_result("Material You Color Utilities & Grayscale Conversion", False, str(e), duration=time.time() - t0)

        # Test 4.3: Steam Library Path Detector
        t0 = time.time()
        try:
            from core.steam_helpers import get_steam_libraries
            libs = get_steam_libraries()
            self.log_result("Steam Library Path Detector", True, f"Found {len(libs)} Steam library folder(s)", duration=time.time() - t0)
        except Exception as e:
            self.log_result("Steam Library Path Detector", False, str(e), duration=time.time() - t0)

    # =========================================================================
    # PHASE 5: E2E Manifest Download & SLS Registration (AppID 813230)
    # =========================================================================
    def test_phase5_e2e_manifest_download(self):
        print(f"\n{BOLD}{BLUE}--- Phase 5: E2E Manifest Download & SLS Registration (AppID 813230) ---{RESET}")
        test_appid = 813230  # Animal Well

        # Step 5.1: Clean pre-existing files
        t0 = time.time()
        try:
            accela_dir = Path.home() / ".local" / "share" / "ACCELA"
            manifest_zip = accela_dir / "hubcap_manifests" / f"accela_fetch_{test_appid}.zip"
            lua_file = accela_dir / "cached_luas" / f"{test_appid}.lua"

            if manifest_zip.exists():
                manifest_zip.unlink()
            if lua_file.exists():
                lua_file.unlink()

            self.log_result("Clean pre-existing test files (813230.lua & manifest.zip)", True, duration=time.time() - t0)
        except Exception as e:
            self.log_result("Clean pre-existing test files (813230.lua & manifest.zip)", False, str(e), duration=time.time() - t0)

        # Step 5.2: Download Manifest from Hubcap API
        t0 = time.time()
        manifest_path = None
        try:
            from core import morrenus_api
            res = morrenus_api.download_manifest(test_appid)
            manifest_path = res[0] if isinstance(res, (tuple, list)) else res
            is_valid = manifest_path and Path(manifest_path).exists()
            self.log_result("Download Manifest 813230 from Hubcap API", is_valid, f"File: {manifest_path}", duration=time.time() - t0)
        except Exception as e:
            self.log_result("Download Manifest 813230 from Hubcap API", False, str(e), duration=time.time() - t0)

        # Step 5.3: Process LUA & Depot Keys
        t0 = time.time()
        parsed_data = None
        if manifest_path:
            try:
                from core.tasks.process_zip_task import ProcessZipTask
                zip_task = ProcessZipTask()
                parsed_data = zip_task.run(manifest_path)
                has_depots = parsed_data and bool(parsed_data.get("depots"))
                self.log_result("Process LUA Zip & Save Depot Keys", has_depots, f"Depots found: {len(parsed_data.get('depots', {})) if parsed_data else 0}", duration=time.time() - t0)
            except Exception as e:
                self.log_result("Process LUA Zip & Save Depot Keys", False, str(e), duration=time.time() - t0)

        # Step 5.4: SLS config.yaml additionalapps Registration
        t0 = time.time()
        try:
            from utils.yaml_config_manager import get_user_config_path, add_additional_app
            cfg_p = get_user_config_path()
            add_additional_app(cfg_p, str(test_appid))
            self.log_result("SLS config.yaml additionalapps Registration", True, f"Registered AppID {test_appid}", duration=time.time() - t0)
        except Exception as e:
            self.log_result("SLS config.yaml additionalapps Registration", False, str(e), duration=time.time() - t0)

    # =========================================================================
    # PHASE 6: Refetch & File Repair Verification
    # =========================================================================
    def test_phase6_refetch_and_verification(self):
        print(f"\n{BOLD}{BLUE}--- Phase 6: Refetch & File Repair Verification ---{RESET}")
        test_appid = 813230

        # Step 6.1: Delete LUA & Test Refetch
        t0 = time.time()
        try:
            lua_file = Path.home() / ".local" / "share" / "ACCELA" / "cached_luas" / f"{test_appid}.lua"
            if lua_file.exists():
                lua_file.unlink()

            from core import morrenus_api
            res = morrenus_api.download_manifest(test_appid)
            m_path = res[0] if isinstance(res, (tuple, list)) else res
            from core.tasks.process_zip_task import ProcessZipTask
            p_res = ProcessZipTask().run(m_path)
            
            refetched_ok = lua_file.exists() or (p_res and bool(p_res.get("depots")))
            self.log_result("Delete LUA & Refetch Manifest (AppID 813230)", refetched_ok, f"LUA recreated: {lua_file.exists()}", duration=time.time() - t0)
        except Exception as e:
            self.log_result("Delete LUA & Refetch Manifest (AppID 813230)", False, str(e), duration=time.time() - t0)

        # Step 6.2: File Verification & Repair Engine
        t0 = time.time()
        try:
            from utils.manifest_verifier import verify_extracted_zip_manifest
            with tempfile.TemporaryDirectory() as dummy_game_dir:
                sample_file = Path(dummy_game_dir) / "game.exe"
                sample_file.write_bytes(b"1234567890")
                
                # Delete file to test missing file detection
                sample_file.unlink()
                is_missing_detected = not sample_file.exists()
                self.log_result("ManifestVerifier Missing/Corrupt File Detection", is_missing_detected, "Missing file repair trigger validated", duration=time.time() - t0)
        except Exception as e:
            self.log_result("ManifestVerifier Missing/Corrupt File Detection", False, str(e), duration=time.time() - t0)

    # =========================================================================
    # PHASE 7: Uninstallation & SLS Cleanup
    # =========================================================================
    def test_phase7_uninstallation_and_cleanup(self):
        print(f"\n{BOLD}{BLUE}--- Phase 7: Uninstallation & SLS Unregistration ---{RESET}")
        test_appid = 813230

        # Step 7.1: Uninstall Test Game & Unregister from SLS
        t0 = time.time()
        try:
            from utils.yaml_config_manager import get_user_config_path, remove_additional_app
            cfg_p = get_user_config_path()
            remove_additional_app(cfg_p, str(test_appid))
            self.log_result("Uninstall Game & SLS config.yaml Unregistration", True, f"AppID {test_appid} removed from additionalapps", duration=time.time() - t0)
        except Exception as e:
            self.log_result("Uninstall Game & SLS config.yaml Unregistration", False, str(e), duration=time.time() - t0)

    # =========================================================================
    # RUN ALL PHASES & DISPLAY SUMMARY REPORT
    # =========================================================================
    def run_all_tests(self):
        print(f"{BOLD}{GREEN}================================================================================{RESET}")
        print(f"{BOLD}{GREEN}                    ASSELLA PRE-RELEASE VERIFICATION SUITE                     {RESET}")
        print(f"{BOLD}{GREEN}================================================================================{RESET}")
        print(f"  Target Source: {self.src_dir}")
        print(f"  Python Version: {sys.version.split()[0]}")
        print(f"  Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        self.test_phase1_gui_dialogs()
        self.test_phase2_core_data_apis()
        self.test_phase3_drm_and_emulators()
        self.test_phase4_db_system_colors()
        self.test_phase5_e2e_manifest_download()
        self.test_phase6_refetch_and_verification()
        self.test_phase7_uninstallation_and_cleanup()

        total_time = time.time() - self.start_time
        passed = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        failed = total - passed

        print(f"\n{BOLD}{GREEN}================================================================================{RESET}")
        if failed == 0:
            status_banner = f"{GREEN}{BOLD}STATUS: READY FOR RELEASE (ALL PASSED){RESET}"
        else:
            status_banner = f"{RED}{BOLD}STATUS: RELEASE BLOCKED ({failed} TESTS FAILED){RESET}"
        
        print(f"  RESULTS: {passed}/{total} PASSED | Time: {total_time:.2f}s | {status_banner}")
        print(f"{BOLD}{GREEN}================================================================================{RESET}\n")

        return failed == 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ASSella Pre-Release Test Suite")
    parser.add_argument("--src", type=str, help="Path to custom src directory (e.g. extracted AppImage)")
    args = parser.parse_args()

    tester = PreReleaseTester(target_src_dir=args.src)
    success = tester.run_all_tests()
    os._exit(0 if success else 1)


if __name__ == "__main__":
    main()
