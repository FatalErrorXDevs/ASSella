import logging
import traceback
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from utils.helpers import get_base_path
from utils.settings import get_settings

logger = logging.getLogger(__name__)

try:
    from core.steam_api import batched_get_product_info
except ImportError:
    # For testing purposes
    batched_get_product_info = None


class ManifestCheckTask(QObject):
    """
    Asynchronous task to check game updates by comparing .depot files
    with current Steam API manifest data without updating the database.
    """

    # Signals
    game_update_checked = pyqtSignal(str, str)  # (appid, update_status)
    progress = pyqtSignal(int, int)  # (current, total)
    batch_progress = pyqtSignal(int, int)  # (current_batch, total_batches)
    completed = pyqtSignal()
    error = pyqtSignal(tuple)  # (Exception, message, traceback)

    def __init__(self, games_list):
        """
        Args:
            games_list: List of game dictionaries to check
        """
        super().__init__()
        self.games_list = games_list
        self._is_running = False

    def run(self):
        """Run the update checks asynchronously using batched API calls"""
        logger.info(f"Starting async update check for {len(self.games_list)} games")
        self._is_running = True

        try:
            total_games = len(self.games_list)
            checked_games = 0

            # Collect all valid appids
            valid_games = []
            for game in self.games_list:
                # Check if task was stopped
                if not self._is_running:
                    logger.debug("Update check task was stopped, exiting")
                    return

                appid = game.get("appid")

                # Skip invalid appids
                if not appid or appid in ("0", "N/A", "unknown"):
                    logger.debug(f"Skipping update check for invalid appid: {appid}")
                    checked_games += 1
                    self.progress.emit(checked_games, total_games)
                    continue

                valid_games.append(game)

            if not valid_games:
                logger.warning("No valid games to check")
                return

            logger.info(f"Valid games to check: {len(valid_games)}")

            # Read tokens from depot files for token-gated apps
            access_tokens = {}
            additional_appids = set()
            for game in valid_games:
                appid = game.get("appid")
                depot_file = Path(get_base_path()) / "depots" / f"{appid}.depot"
                if depot_file.exists():
                    try:
                        content = depot_file.read_text().strip()
                        parts = content.split(":", 2)
                        
                        if parts and parts[0].strip():
                            main_depot_id = parts[0].strip()
                            additional_appids.add(main_depot_id)
                            
                        if len(parts) >= 3 and parts[2].strip():
                            access_tokens[appid] = parts[2].strip()
                            if 'main_depot_id' in locals():
                                access_tokens[main_depot_id] = parts[2].strip()
                    except OSError:
                        pass

            # Use batched API call for all valid games and any DLC depot IDs
            appid_list = list({game["appid"] for game in valid_games} | additional_appids)
            batch_size = 20
            rate_limit_delay = 0.3

            # Calculate number of batches for progress reporting
            num_batches = (len(appid_list) + batch_size - 1) // batch_size
            logger.info(
                f"Will process {len(appid_list)} appids in {num_batches} batches"
            )

            # Fetch all data in batched calls
            if batched_get_product_info is None:
                logger.warning(
                    "batched_get_product_info is not available; skipping API fetch and assuming no data."
                )
                batched_results = {}
            else:
                batched_results = batched_get_product_info(
                    appid_list,
                    access_tokens=access_tokens,
                    batch_size=batch_size,
                    rate_limit_delay=rate_limit_delay,
                    is_cancelled=lambda: not self._is_running,
                    request_timeout=10,
                )

            if not self._is_running:
                logger.debug("Update check task was stopped after batched fetch")
                return

            # Process each game with the batched results
            for game in valid_games:
                # Check if task was stopped
                if not self._is_running:
                    break

                appid = game.get("appid")

                try:
                    # Use batched results to determine update status
                    update_status = self._check_game_update_with_batched_data(
                        game, batched_results
                    )
                    # Emit signal with results
                    self.game_update_checked.emit(appid, update_status)

                except Exception as e:
                    logger.error(f"Error checking update for game {appid}: {e}")
                    self.error.emit((type(e), str(e), traceback.format_exc()))
                    self.game_update_checked.emit(appid, "cannot_determine")

                checked_games += 1
                self.progress.emit(checked_games, total_games)

            logger.info("Async update check complete")

        finally:
            self.completed.emit()

    @staticmethod
    def _check_game_update_with_batched_data(game_data, batched_results):
        """
        Check if a game has an update available using pre-fetched batched data.

        This method uses the results from a batched API call to determine if a game
        has an update, comparing the saved manifest ID with the current public manifest ID.

        Args:
            game_data: Dictionary containing game information
            batched_results: Dict mapping appid -> product_info from batched_get_product_info()

        Returns:
            str: Status constant ('update_available', 'up_to_date', 'cannot_determine')
        """
        appid = game_data.get("appid")

        # Skip if no valid appid
        if not appid or appid in ("0", "N/A", "unknown"):
            return "cannot_determine"

        # DLC-Only mode: check only the user-selected depots, not the whole game
        try:
            from utils.settings import get_settings
            import json as _json
            _s = get_settings()
            if _s.value(f"dlc_only_mode/{appid}", False, type=bool):
                val = _s.value(f"depot_selection/{appid}", "", type=str)
                if val:
                    saved_selection = _json.loads(val)
                    selected_depot_ids = saved_selection.get("selected", [])
                    if selected_depot_ids:
                        return ManifestCheckTask._check_dlc_only_update(
                            appid, selected_depot_ids, batched_results, game_data
                        )
        except Exception as _e:
            logger.debug(f"DLC-only mode check failed for {appid}: {_e}")

        # Read saved manifest ID from depot file
        depots_dir = Path(get_base_path()) / "depots"
        depot_file = depots_dir / f"{appid}.depot"

        if not depot_file.exists():
            # No saved manifest file, cannot determine version
            logger.debug(f"Depot file not found for app {appid}: {depot_file}")
            return "cannot_determine"

        # Read the saved manifest ID
        try:
            with open(depot_file, "r") as f:
                content = f.read().strip()
                if ":" not in content:
                    logger.warning(f"Invalid depot file format for {appid}")
                    return "cannot_determine"

                parts = content.split(":", 2)
                if len(parts) == 2:
                    saved_main_depot_id, saved_manifest_id = parts
                elif len(parts) >= 3:
                    saved_main_depot_id, saved_manifest_id, _ = parts
                else:
                    logger.warning(f"Invalid depot file format for {appid}")
                    return "cannot_determine"

                saved_main_depot_id = saved_main_depot_id.strip()
                saved_manifest_id = saved_manifest_id.strip()
        except Exception as e:
            logger.error(f"Error reading depot file {depot_file}: {e}")
            return "cannot_determine"

        # Get current manifest from batched results
        try:
            # Look for the appid in batched results
            steam_client_data = batched_results.get(appid, {})
            depots = steam_client_data.get("depots", {})
            
            # If depot isn't in base game, try falling back to the DLC AppID (which is queried via saved_main_depot_id)
            if saved_main_depot_id not in depots and saved_main_depot_id in batched_results:
                dlc_data = batched_results[saved_main_depot_id]
                dlc_depots = dlc_data.get("depots", {})
                if saved_main_depot_id in dlc_depots:
                    depots = dlc_depots
                    logger.debug(f"Resolved depot {saved_main_depot_id} via DLC info instead of base game {appid}")
                    
            if not depots:
                logger.debug(f"No depot info found for app {appid} or its depot {saved_main_depot_id}")
                return "cannot_determine"

            # Find the matching depot
            if saved_main_depot_id in depots:
                depot_info = depots[saved_main_depot_id]
                current_manifest_id = depot_info.get("manifest_id")

                if current_manifest_id:
                    # Save the latest manifest ID to settings for tracking
                    settings = get_settings()
                    settings.setValue(f"latest_steam_manifest_id/{appid}", current_manifest_id)

                    # If this game is already marked as update available, check if the pre-fetched manifest is stale
                    if game_data.get("update_status") == "update_available":
                        fetched_id = settings.value(f"fetched_manifest_id/{appid}", "", type=str)
                        if fetched_id and fetched_id != current_manifest_id:
                            logger.info(
                                f"App {appid} has a newer update on Steam ({current_manifest_id}) "
                                f"than the pre-fetched manifest ({fetched_id}). Marking manifest as stale."
                            )
                            settings.setValue(f"manifest_is_fresh/{appid}", False)
                        elif not fetched_id:
                            # Seed fetched_manifest_id with current manifest for future checks
                            settings.setValue(f"fetched_manifest_id/{appid}", current_manifest_id)

                    # Compare manifest IDs
                    if saved_manifest_id != current_manifest_id:
                        logger.info(
                            f"Update available for app {appid}: saved={saved_manifest_id}, current={current_manifest_id}"
                        )
                        return "update_available"
                    else:
                        return "up_to_date"
                else:
                    return "cannot_determine"
            else:
                return "cannot_determine"

        except Exception as e:
            logger.error(f"Error checking for updates for app {appid}: {e}")
            return "cannot_determine"

    @staticmethod
    def _get_depot_latest_manifest(depot_id: str, appid: str, batched_results: dict) -> str:
        # 1. Try in base game depots
        base_depots = batched_results.get(appid, {}).get("depots", {})
        if depot_id in base_depots:
            return base_depots[depot_id].get("manifest_id")

        # 2. Try in batched_results[depot_id] directly
        dlc_depots = batched_results.get(depot_id, {}).get("depots", {})
        if depot_id in dlc_depots:
            return dlc_depots[depot_id].get("manifest_id")

        return None

    @staticmethod
    def _get_installed_depot_manifest(depot_id: str, game_data: dict) -> str:
        install_path = game_data.get("install_path")
        if not install_path or not os.path.exists(install_path):
            return None

        ddm_dir = os.path.join(install_path, ".DepotDownloader")
        if not os.path.exists(ddm_dir):
            return None

        try:
            for fname in os.listdir(ddm_dir):
                if fname.startswith(f"{depot_id}_") and fname.endswith(".manifest"):
                    # Extract the manifest ID: depotId_manifestId.manifest
                    base = fname[:-9]  # strip ".manifest"
                    parts = base.split("_", 1)
                    if len(parts) == 2:
                        return parts[1]
        except Exception:
            pass
        return None

    @staticmethod
    def _check_dlc_only_update(appid, selected_depot_ids, batched_results, game_data):
        has_changes = False
        any_resolved = False

        for depot_id in selected_depot_ids:
            depot_id_str = str(depot_id)
            latest_manifest = ManifestCheckTask._get_depot_latest_manifest(depot_id_str, appid, batched_results)
            if not latest_manifest:
                continue

            any_resolved = True
            installed_manifest = ManifestCheckTask._get_installed_depot_manifest(depot_id_str, game_data)

            # If we don't have it installed yet, or it matches, it's not a pending update
            if installed_manifest and installed_manifest != latest_manifest:
                logger.info(
                    f"[DLC Only Check] Update available for depot {depot_id_str} "
                    f"of app {appid}: installed={installed_manifest}, latest={latest_manifest}"
                )
                has_changes = True

        if has_changes:
            return "update_available"
        if any_resolved:
            return "up_to_date"
        return "cannot_determine"

    def stop(self):
        """Stop the task"""
        logger.debug("Stopping manifest check task")
        self._is_running = False
