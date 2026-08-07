import logging
import os
import re
import shutil
import subprocess
import sys

from PyQt6.QtCore import QObject, pyqtSignal

from utils.helpers import (
    get_slscheevo_save_path,
    get_schema_grabber_path,
    get_steam_stats_dir,
    get_dotnet_env,
)
from utils.paths import Paths

logger = logging.getLogger(__name__)

# Handle optional psutil import
try:
    import psutil
except ImportError:
    psutil = None
    logger.debug("psutil not found, process termination will be less robust.")


class GenerateAchievementsTask(QObject):
    """Generate Steam achievement stats using schema-grabber"""

    progress = pyqtSignal(str)
    progress_percentage = pyqtSignal(int)
    completed = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._is_running = True
        self.process = None
        self.process_pid = None

    def run(self, app_ids=None):
        """Run schema-grabber to generate achievement stats"""
        logger.info("Starting achievement generation task using schema-grabber")
        self.progress.emit("Checking Steam credentials...")

        try:
            # Get credentials from settings
            from utils.settings import get_settings
            settings = get_settings()
            settings.sync()
            username = settings.value("steam_username", "", type=str)
            from utils.helpers import decrypt_string
            password = decrypt_string(settings.value("steam_password", "", type=str))

            if not username or not password:
                error_msg = (
                    "Steam credentials not configured in settings. "
                    "Please open Settings -> Tools and set your Steam Username and Password."
                )
                self.progress.emit(error_msg)
                self.error.emit(error_msg)
                result = {"success": False, "message": error_msg}
                self.completed.emit(result)
                return result

            schema_grabber = get_schema_grabber_path()
            if not schema_grabber.exists():
                error_msg = f"schema-grabber binary not found at {schema_grabber}."
                self.progress.emit(error_msg)
                self.error.emit(error_msg)
                result = {"success": False, "message": error_msg}
                self.completed.emit(result)
                return result

            self.progress.emit("schema-grabber binary found")
            logger.info(f"schema-grabber binary found at: {schema_grabber}")

            # Resolve target app IDs
            target_appids = []
            if app_ids:
                if isinstance(app_ids, list):
                    target_appids = [str(aid) for aid in app_ids]
                else:
                    target_appids = [str(app_ids)]
            else:
                target_appids = ["0"]

            # Run directory
            cwd = get_slscheevo_save_path() / "data" / "bins"
            cwd.mkdir(parents=True, exist_ok=True)

            success_count = 0
            failed_count = 0
            last_error = ""

            for idx, app_id in enumerate(target_appids, 1):
                self.progress.emit(f"Generating stats schema for game ID {app_id}...")
                
                # Command line run: schema-grabber username password appId
                command = [str(schema_grabber), username, password, app_id]
                logger.info(f"Executing schema-grabber for AppID {app_id}")

                # Resolve dotnet environment settings (cleaning overrides and setting DOTNET_ROOT)
                env = get_dotnet_env()

                self.process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    cwd=str(cwd),
                    env=env,
                    bufsize=1,  # Line buffered
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    ),
                )
                self.process_pid = self.process.pid

                # Start a watchdog thread to terminate the process if it hangs (e.g. on 2FA prompts)
                import threading
                def watchdog():
                    import time
                    start_time = time.time()
                    while time.time() - start_time < 25:
                        if self.process is None or self.process.poll() is not None:
                            return
                        time.sleep(0.5)
                    if self.process is not None and self.process.poll() is None:
                        logger.warning(f"schema-grabber exceeded 25 seconds timeout for AppID {app_id}. Terminating...")
                        self.stop()

                threading.Thread(target=watchdog, daemon=True).start()

                # Read output
                while True:
                    if not self._is_running:
                        self.process.terminate()
                        break

                    if self.process is None or self.process.stdout is None:
                        break

                    line = self.process.stdout.readline()
                    if not line:
                        return_code = self.process.poll()
                        if return_code is not None:
                            break
                        continue

                    line = line.rstrip()
                    # Hide password if printed in output
                    safe_line = line.replace(password, "********")
                    self.progress.emit(safe_line)

                    # Update percentage roughly
                    percentage = int((idx / len(target_appids)) * 100)
                    self.progress_percentage.emit(percentage)

                return_code = self.process.wait()
                self.process = None
                self.process_pid = None

                if return_code == 0:
                    success_count += 1
                else:
                    failed_count += 1
                    last_error = f"schema-grabber exited with code {return_code}"

            # Copy generated files to Steam directory
            if success_count > 0:
                # Copy template stats file UserGameStats_{account_id}_{appid}.bin for each logged in account
                try:
                    steam_stats_dir = get_steam_stats_dir()
                    if steam_stats_dir:
                        login_users_file = steam_stats_dir.parent / "config" / "loginusers.vdf"
                        if login_users_file.exists():
                            import vdf
                            with open(login_users_file, "r", encoding="utf-8") as f:
                                loginusers = vdf.load(f)
                            accounts = loginusers.get("users", {})

                            template_path = get_slscheevo_save_path() / "data" / "UserGameStats_TEMPLATE.bin"
                            if not template_path.exists():
                                template_path = Paths.deps("SLScheevo/data/UserGameStats_TEMPLATE.bin")

                            if template_path.exists():
                                for steamid64_str in accounts.keys():
                                    for app_id in target_appids:
                                        if app_id == "0":
                                            continue
                                        try:
                                            steamid64 = int(steamid64_str)
                                            account_id = steamid64 & 0xFFFFFFFF
                                            stats_name = f"UserGameStats_{account_id}_{app_id}.bin"
                                            archive_stats = cwd / stats_name
                                            if not archive_stats.exists():
                                                shutil.copy2(template_path, archive_stats)
                                                logger.info(f"Generated user stats from template: {stats_name}")
                                        except Exception as e:
                                            logger.warning(f"Failed to generate template stats: {e}")
                except Exception as e:
                    logger.warning(f"Template stats generator failed: {e}")

                # Copy all generated bin files to Steam stats
                try:
                    steam_stats_dir = get_steam_stats_dir()
                    if steam_stats_dir:
                        steam_stats_dir.mkdir(parents=True, exist_ok=True)
                    
                    bin_files = list(cwd.glob("**/*.bin"))
                    for bin_file in bin_files:
                        if steam_stats_dir:
                            dest_path = steam_stats_dir / bin_file.name
                            if bin_file.name.startswith("UserGameStatsSchema_") or not dest_path.exists():
                                shutil.copy2(bin_file, dest_path)
                                logger.info(f"Copied {bin_file.name} to {dest_path}")
                except Exception as e:
                    logger.warning(f"Failed to copy bins to Steam stats: {e}")

            if failed_count == 0:
                msg = "Achievement generation completed successfully"
                self.progress.emit(msg)
                result = {"success": True, "return_code": 0, "message": msg}
                self.completed.emit(result)
                return result
            else:
                msg = last_error if last_error else "Achievement generation failed"
                self.progress.emit(msg)
                self.error.emit(msg)
                result = {"success": False, "return_code": -1, "message": msg}
                self.completed.emit(result)
                return result

        except Exception as e:
            error_msg = f"Unexpected error during achievement generation: {e}"
            self.progress.emit(f"{error_msg}")
            logger.error(error_msg, exc_info=True)
            if self.process:
                self.process.terminate()
            self.process = None
            self.process_pid = None
            self.error.emit(error_msg)
            result = {"success": False, "return_code": -1, "message": error_msg}
            self.completed.emit(result)
            return result

    def stop(self):
        """Stop the task and terminate the process"""
        logger.debug("Stop signal received by achievement generation task")
        self._is_running = False

        if not self.process_pid:
            self.process = None
            return

        if psutil:
            try:
                parent = psutil.Process(self.process_pid)
                children = parent.children(recursive=True)
                processes = [parent] + children
                for proc in processes:
                    try:
                        proc.terminate()
                    except psutil.NoSuchProcess:
                        pass
                # Wait for graceful termination
                gone, alive = psutil.wait_procs(processes, timeout=3)
                for p in alive:
                    p.kill()  # Force kill stubborn processes
            except psutil.NoSuchProcess:
                pass
            except Exception as e:
                logger.error(f"Error stopping process with psutil: {e}")
        else:
            if self.process:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=3)
                except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
                    try:
                        self.process.kill()
                        self.process.wait(timeout=3)
                    except (ProcessLookupError, OSError):
                        pass
        self.process = None
        self.process_pid = None

