"""
SLSsteam Integration Module

Centralized handler for SLSsteam-based install/uninstall operations.
When experimental_acf_independent is enabled, ASSella delegates all ACF
manifest management to Steam natively via SLSsteam's API pipe.

Flow for install/update:
  1. Write appid to config.yaml in-place (preserves inode → inotify fires)
  2. Wait for SLSsteam to acknowledge (log polling, capped fallback)
  3. Send install|appid|0 to /tmp/SLSsteam.API
  4. Optionally verify ACF creation (non-blocking)

Flow for uninstall:
  1. Send uninstall|appid to /tmp/SLSsteam.API
  2. Remove appid from config.yaml in-place

If Steam/SLSsteam is unavailable:
  - Config is still written → Steam will process on next launch
  - API calls fail silently → game shows as "installed" via metadata fallback
  - ASSella's metadata.json serves as the source of truth for library scanning
"""

import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SLSSTEAM_LOG_PATH = Path.home() / ".SLSsteam.log"
SLSSTEAM_API_PIPE = "/tmp/SLSsteam.API"
MAX_CONFIG_WAIT_SECONDS = 10
MAX_ACF_VERIFY_SECONDS = 10


def _experimental_mode_enabled() -> bool:
    try:
        from utils.settings import get_settings
        return get_settings().value("experimental_acf_independent", False, type=bool)
    except Exception:
        return False


def _is_slssteam_available() -> bool:
    """Check if SLSsteam API pipe exists and Steam is running."""
    if sys.platform != "linux":
        return False
    return os.path.exists(SLSSTEAM_API_PIPE)


def _slssteam_api_send(command: str) -> bool:
    """Send a raw command to SLSsteam via the named pipe."""
    if not _is_slssteam_available():
        return False
    try:
        with open(SLSSTEAM_API_PIPE, "w") as f:
            f.write(command)
            f.flush()
        logger.info(f"SLSsteam API command sent: {command}")
        return True
    except OSError:
        logger.warning(f"SLSsteam API pipe write failed for: {command}")
        return False


def _poll_sls_log_for(pattern: str, timeout_seconds: int = MAX_CONFIG_WAIT_SECONDS, start_offset: int = 0) -> bool:
    """Poll SLSsteam log for a regex pattern in NEW content only. Returns True if found."""
    if not SLSSTEAM_LOG_PATH.exists():
        return False

    compiled = re.compile(pattern)
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            current_size = SLSSTEAM_LOG_PATH.stat().st_size
            if current_size > start_offset:
                with open(SLSSTEAM_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(start_offset)
                    for line in f:
                        if compiled.search(line):
                            return True
                start_offset = current_size
        except (OSError, IOError):
            pass
        time.sleep(0.3)

    return False


def _get_sls_log_size() -> int:
    """Return current SLS log file size for offset-based polling."""
    try:
        return SLSSTEAM_LOG_PATH.stat().st_size if SLSSTEAM_LOG_PATH.exists() else 0
    except (OSError, IOError):
        return 0


def _write_appid_to_config(appid: str, game_name: str = "") -> bool:
    """Write appid into SLSsteam config.yaml AdditionalApps in-place."""
    from utils.yaml_config_manager import get_user_config_path, add_additional_app
    config_path = get_user_config_path()
    comment = game_name if game_name else ""
    return add_additional_app(config_path, str(appid), comment)


def _remove_appid_from_config(appid: str) -> bool:
    """Remove appid from SLSsteam config.yaml AdditionalApps in-place."""
    from utils.yaml_config_manager import get_user_config_path, remove_additional_app
    config_path = get_user_config_path()
    return remove_additional_app(config_path, str(appid))


def _wait_for_sls_license(appid: str, log_offset: int) -> bool:
    """Wait for SLSsteam to fully process config change AND unlock the license.
    Must poll for AppLicensesChanged or Unlocked log lines, then wait briefly for
    SLSsteam to propagate the license in Steam memory before API install is sent.
    """
    pattern = rf"(?:AppLicensesChanged callback invoked for {re.escape(str(appid))}|Unlocked {re.escape(str(appid))})"
    found = _poll_sls_log_for(
        pattern,
        timeout_seconds=MAX_CONFIG_WAIT_SECONDS,
        start_offset=log_offset,
    )
    if found:
        logger.info(f"SLSsteam license for {appid} confirmed via log — sleeping 1.5s for memory propagation")
        time.sleep(1.5)
    else:
        logger.info(f"SLSsteam license for {appid} not confirmed via log — proceeding anyway")
    return found


def _verify_acf_created(appid: str, timeout: Optional[float] = None) -> bool:
    """Poll for ACF manifest creation by Steam across all known library paths."""
    acf_filename = f"appmanifest_{appid}.acf"

    # Steam always creates ACFs in the primary library first
    steam_home = Path.home() / ".local" / "share" / "Steam"
    candidate_paths = [steam_home / "steamapps" / acf_filename]

    # Also check any external libraries
    try:
        vdf_path = steam_home / "steamapps" / "libraryfolders.vdf"
        if vdf_path.exists():
            with open(vdf_path, "r", encoding="utf-8") as f:
                for line in f:
                    m = re.search(r'"path"\s+"([^"]+)"', line)
                    if m:
                        candidate_paths.append(
                            Path(m.group(1)) / "steamapps" / acf_filename
                        )
    except (OSError, IOError):
        pass

    verify_seconds = timeout if timeout is not None else MAX_ACF_VERIFY_SECONDS
    deadline = time.time() + verify_seconds
    while time.time() < deadline:
        for p in candidate_paths:
            if p.exists():
                logger.info(f"Steam created ACF manifest for {appid} at {p}")
                return True
        time.sleep(0.5)

    searched = ", ".join(str(p) for p in candidate_paths)
    logger.warning(
        f"ACF manifest for {appid} not found after {verify_seconds}s. "
        f"Searched: {searched} — Steam may create it later"
    )
    return False


def _silent_background_retry_pipe(appid: str, library_index: int, max_retries: int = 12) -> None:
    """Silent background worker thread to retry install pipe command if Steam was delayed."""
    import threading

    def _retry_worker():
        for i in range(max_retries):
            time.sleep(5)
            if _verify_acf_created(appid, timeout=1.0):
                logger.info(f"Silent retry confirmed ACF manifest created for AppID {appid} on retry {i + 1}")
                return
            logger.info(f"Silent background retry ({i + 1}/{max_retries}) sending install|{appid}|{library_index}...")
            _slssteam_api_send(f"install|{appid}|{library_index}")

    t = threading.Thread(target=_retry_worker, daemon=True)
    t.start()


def install_via_sls(appid: str, game_name: str = "", library_path: str = "") -> bool:
    """
    Register a game with Steam via SLSsteam.

    Writes appid to SLS config, waits for SLS to process,
    then sends install API command to Steam.

    Returns True if the API call was sent successfully.
    Does NOT fail if Steam is unavailable — config write alone is sufficient
    for Steam to register the game on next launch.
    """
    if not _experimental_mode_enabled():
        logger.debug("SLSsteam experimental mode disabled — skipping install")
        return False

    if not appid or appid in ("0", "N/A", "unknown"):
        return False

    # 1. Write to config in-place
    written = _write_appid_to_config(appid, game_name)
    if not written:
        logger.info(f"AppID {appid} already in SLS config or write failed")
    else:
        logger.info(f"Wrote AppID {appid} to SLS config")

    # 2. Check if SLSsteam is available
    if not _is_slssteam_available():
        logger.info(
            f"SLSsteam/Steam not available — AppID {appid} in config. "
            "Steam will register on next launch."
        )
        return True  # Config write alone is valid

    # 3. Wait for SLS to unlock license — only if newly written to config
    if written:
        log_offset = _get_sls_log_size()
        _wait_for_sls_license(appid, log_offset)

    # 4. Resolve the Steam library index for this install path
    library_index = 0
    if library_path:
        try:
            from core.steam_helpers import get_library_index, find_steam_install
            steam_path = find_steam_install()
            library_index = get_library_index(library_path, steam_path)
            logger.info(f"Resolved library index {library_index} for path: {library_path}")
        except Exception as e:
            logger.warning(f"Could not resolve library index, defaulting to 0: {e}")

    # 5. Send install to Steam
    sent = _slssteam_api_send(f"install|{appid}|{library_index}")
    if not sent:
        logger.warning(f"Failed to send install command for {appid}")
        return True  # Config is still written

    # 6. Verify ACF (non-blocking). If delayed, launch silent background retry
    acf_created = _verify_acf_created(appid)
    if not acf_created:
        logger.info(f"ACF creation delayed for {appid} — launching silent background retry worker...")
        _silent_background_retry_pipe(appid, library_index)

    return True


def uninstall_via_sls(appid: str) -> bool:
    """
    Unregister a game from Steam via SLSsteam.

    Sends uninstall API command to Steam to delete the ACF,
    then removes the appid from SLS config.

    Returns True if both operations were attempted.
    """
    if not _experimental_mode_enabled():
        logger.debug("SLSsteam experimental mode disabled — skipping uninstall")
        return False

    if not appid or appid in ("0", "N/A", "unknown"):
        return False

    success = True

    # 1. Send uninstall to Steam first (before file deletion)
    if _is_slssteam_available():
        sent = _slssteam_api_send(f"uninstall|{appid}")
        if not sent:
            logger.warning(f"Failed to send SLS uninstall for {appid}")
            success = False
    else:
        logger.info(
            f"SLSsteam not available — AppID {appid} still in config. "
            "Will unregister on next launch after manual config removal."
        )

    # 2. Remove from config regardless
    removed = _remove_appid_from_config(appid)
    if not removed:
        logger.debug(f"AppID {appid} not found in SLS config (already removed?)")
    else:
        logger.info(f"Removed AppID {appid} from SLS config")

    return success


def patch_acf_via_sls(appid: str, library_path: str = "") -> bool:
    """
    Re-install an existing game via SLSsteam to fix a missing or stale ACF.
    Used by the 'Fix Manifest' feature in the library UI.
    """
    if not _experimental_mode_enabled():
        return False

    if not appid or appid in ("0", "N/A", "unknown"):
        return False

    if not _is_slssteam_available():
        logger.warning(f"Cannot patch ACF for {appid} — SLSsteam not available")
        return False

    library_index = 0
    if library_path:
        try:
            from core.steam_helpers import get_library_index, find_steam_install
            steam_path = find_steam_install()
            library_index = get_library_index(library_path, steam_path)
        except Exception as e:
            logger.warning(f"Could not resolve library index for patch, defaulting to 0: {e}")

    return _slssteam_api_send(f"install|{appid}|{library_index}")
