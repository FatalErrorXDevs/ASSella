import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from utils.settings import get_settings

logger = logging.getLogger(__name__)

# Note: helpers keep repeated guard/IO logic centralized for clarity.


def _config_management_enabled() -> bool:
    return is_slssteam_mode_enabled() and is_slssteam_config_management_enabled()


def _read_config_content(config_path: Path, log_missing: bool = False) -> Optional[str]:
    if not config_path.exists():
        if log_missing:
            logger.warning(f"Config file not found at {config_path}")
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        return f.read()


_CONFIG_DISABLED = object()


def _get_config_content_if_enabled(config_path: Path, log_missing: bool = False):
    if not _config_management_enabled():
        return _CONFIG_DISABLED
    return _read_config_content(config_path, log_missing=log_missing)


BACKUP_SUFFIX = ".bak"


def is_slssteam_mode_enabled() -> bool:
    """Check if Steam integration is enabled for the current platform."""
    settings = get_settings()
    if sys.platform == "linux":
        return settings.value("library_mode", False, type=bool)
    return settings.value("slssteam_mode", False, type=bool)


def is_greenluma_wrapper_mode_enabled() -> bool:
    """Check if GreenLuma wrapper mode is enabled on Windows."""
    if sys.platform != "win32":
        return False

    settings = get_settings()
    return settings.value("slssteam_mode", False, type=bool)


def is_slssteam_config_management_enabled() -> bool:
    """Check if SLSsteam config management is enabled in settings."""
    settings = get_settings()
    return settings.value("sls_config_management", True, type=bool)


def get_fake_appid_for_online() -> str:
    """Get the FakeAppId to use for playing games online.

    Returns:
        The appid from settings, or "480" (Spacewar) if not set.
    """
    settings = get_settings()
    fake_appid = settings.value("fake_appid_for_online", "", type=str).strip()
    return fake_appid if fake_appid else "480"


def _create_backup(config_path: Path) -> bool:
    """Create a backup of the config file.

    Creates config.yaml.bak with the current config content.
    Only creates backup if source file exists.
    Does not overwrite existing backup if new file is smaller.
    """
    try:
        if not config_path.exists():
            return False

        backup_path = config_path.with_suffix(BACKUP_SUFFIX)

        # Check if backup already exists and new file is smaller
        if backup_path.exists():
            new_size = config_path.stat().st_size
            backup_size = backup_path.stat().st_size
            if new_size < backup_size:
                logger.debug(
                    f"Skipping backup: new file ({new_size} bytes) is smaller "
                    f"than existing backup ({backup_size} bytes)"
                )
                return True

        shutil.copy2(config_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return True
    except OSError as e:
        logger.error(f"Failed to create backup for {config_path}: {e}", exc_info=True)
        return False

def backup_config_on_startup(config_path: Path) -> bool:
    """Create a backup of the config file on application startup."""
    return _create_backup(config_path)


def _atomic_write(config_path: Path, content: str) -> bool:
    """Write content to config file in-place to preserve inode and trigger inotify FileWatcher."""
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        return True
    except OSError as e:
        logger.error(f"Failed to write {config_path}: {e}", exc_info=True)
        return False


def ensure_slssteam_api_enabled(config_path: Path) -> bool:
    """Ensure SLSsteam API is enabled in config.yaml."""
    if not is_slssteam_mode_enabled():
        logger.debug("Steam integration is disabled, skipping API enable check")
        return False
    if not is_slssteam_config_management_enabled():
        logger.debug("SLSsteam config management disabled, skipping API enable check")
        return False
    return update_yaml_boolean_value(config_path, "API", True)


def ensure_slssteam_logging_enabled(config_path: Path) -> bool:
    """Ensure SLSsteam has the Once (0x2) log level enabled in config.yaml.

    Checks both:
      - New SLS bitmask format (LogLevels): ensures bit 1 (0x2 / Once) is set via bitwise OR.
      - Old SLS enum format (LogLevel): ensures level is 0 (Once).

    Preserves indentation, surrounding lines, comments, and file inode.
    """
    if not is_slssteam_mode_enabled():
        logger.debug("Steam integration is disabled, skipping logging enable check")
        return False
    if not is_slssteam_config_management_enabled():
        logger.debug("SLSsteam config management disabled, skipping logging enable check")
        return False

    try:
        if not config_path.exists():
            logger.warning(f"Config file not found at {config_path}")
            return False

        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Check for new bitmask format: "LogLevels: <value>"
        pattern_new = re.compile(
            r"^(\s*)LogLevels\s*:\s*([^\r\n#]+)(.*)$",
            re.MULTILINE,
        )
        match_new = pattern_new.search(content)
        if match_new:
            indent = match_new.group(1)
            raw_val = match_new.group(2).strip().strip('"').strip("'")
            comment = match_new.group(3)

            try:
                if raw_val.lower().startswith("0x"):
                    current_val = int(raw_val, 16)
                else:
                    current_val = int(raw_val, 10)
            except ValueError:
                current_val = 0

            # Check if Once bit (0x2) is already enabled
            if (current_val & 0x2) != 0:
                logger.debug(f"LogLevels in {config_path} already has Once flag enabled (0x{current_val:X})")
                return False

            new_val = current_val | 0x2
            hex_str = f"0x{new_val:X}"
            comment_str = f" {comment.strip()}" if comment.strip() else ""
            replacement = f"{indent}LogLevels: {hex_str}{comment_str}"
            new_content = pattern_new.sub(replacement, content, count=1)

            if not _atomic_write(config_path, new_content):
                return False

            logger.info(f"Updated SLSsteam LogLevels from 0x{current_val:X} to {hex_str} in {config_path}")
            return True

        # 2. Check for old enum format: "LogLevel: <value>"
        pattern_old = re.compile(
            r"^(\s*)LogLevel\s*:\s*([^\r\n#]+)(.*)$",
            re.MULTILINE,
        )
        match_old = pattern_old.search(content)
        if match_old:
            indent = match_old.group(1)
            raw_val = match_old.group(2).strip().strip('"').strip("'")
            comment = match_old.group(3)

            try:
                if raw_val.lower().startswith("0x"):
                    current_val = int(raw_val, 16)
                else:
                    current_val = int(raw_val, 10)
            except ValueError:
                current_val = 0

            # In old enum: Once = 0, Debug = 1, Info = 2, NotifyShort = 3, NotifyLong = 4, Warn = 5, None = 6
            if current_val != 0:
                comment_str = f" {comment.strip()}" if comment.strip() else ""
                replacement = f"{indent}LogLevel: 0{comment_str}"
                new_content = pattern_old.sub(replacement, content, count=1)

                if not _atomic_write(config_path, new_content):
                    return False

                logger.info(f"Updated old SLSsteam LogLevel from {current_val} to 0 in {config_path}")
                return True
            else:
                logger.debug(f"Old LogLevel in {config_path} is already 0 (Once)")
                return False

        logger.debug(f"No LogLevels/LogLevel key found in {config_path} (default enables all)")
        return False

    except OSError as e:
        logger.error(f"Failed to ensure SLSsteam logging in {config_path}: {e}", exc_info=True)
        return False


def ensure_slssteam_prerequisites(config_path: Optional[Path] = None) -> bool:
    """Silently ensure all SLSsteam configuration prerequisites are met.

    Specifically ensures:
      1. API: yes (for communication via /tmp/SLSsteam.API)
      2. LogLevels has 0x2 / Once flag enabled (or old LogLevel: 0)

    Creates a backup before applying any modifications and performs in-place atomic writes.
    Never shows disruptive UI popups — logs actions at INFO/DEBUG level.
    """
    if config_path is None:
        config_path = get_user_config_path()

    if not config_path.exists():
        logger.debug(f"ensure_slssteam_prerequisites: Config not found at {config_path}")
        return False

    if not is_slssteam_config_management_enabled():
        logger.debug("ensure_slssteam_prerequisites: SLS config management disabled in settings")
        return False

    changed = False
    _create_backup(config_path)

    try:
        if ensure_slssteam_api_enabled(config_path):
            changed = True
            logger.info("Silently ensured SLSsteam API is enabled in config.yaml")

        if ensure_slssteam_logging_enabled(config_path):
            changed = True
            logger.info("Silently ensured SLSsteam LogLevels includes 0x2 (Once) in config.yaml")
    except Exception as e:
        logger.warning(f"Error ensuring SLSsteam prerequisites: {e}")

    return changed



def update_yaml_boolean_value(config_path: Path, key: str, value: bool) -> bool:
    """Update a boolean value in YAML config using regex pattern matching."""
    try:
        if not config_path.exists():
            logger.warning(f"Config file not found at {config_path}")
            return False

        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Regex pattern to match the key with its current value
        pattern = re.compile(
            r"^(\s*)"
            + re.escape(key)
            + r"\s*:\s*(yes|no|true|false|Yes|No|True|False)\b",
            re.MULTILINE,
        )

        match = pattern.search(content)
        if not match:
            logger.warning(f"Key '{key}' not found in config file {config_path}")
            return False

        indent = match.group(1)
        old_value = match.group(2)

        # Always use yes/no format for SLSsteam compatibility
        new_value = "yes" if value else "no"

        # Check if already set correctly
        if old_value.lower() == new_value.lower():
            logger.debug(f"Key '{key}' is already set to {new_value}")
            return False

        # Create replacement string preserving indentation
        replacement = f"{indent}{key}: {new_value}"

        # Replace only the matched line
        new_content = pattern.sub(replacement, content)

        if not _atomic_write(config_path, new_content):
            return False

        logger.info(f"Updated '{key}' to {new_value} in {config_path}")
        return True

    except OSError as e:
        logger.error(f"Failed to update '{key}' in {config_path}: {e}", exc_info=True)
        return False


def get_user_config_path() -> Path:
    """Get the path to the user's SLSsteam config.yaml file.

    Delegates to SteamEnv for Flatpak-aware path resolution:
      - Flatpak Steam: ~/.var/app/com.valvesoftware.Steam/.config/SLSsteam/config.yaml
      - Native Steam:  $XDG_CONFIG_HOME/SLSsteam/config.yaml  (or ~/.config/SLSsteam/config.yaml)

    Emits a warning if the resolved config does not exist yet.
    """
    try:
        from core.steam_helpers import get_steam_env
        env = get_steam_env()
        config_path = env.sls_config_path
        if not config_path.exists():
            logger.warning(
                f"SLSsteam config.yaml not found at expected location: {config_path}. "
                f"(Steam type: {'Flatpak' if env.is_flatpak else 'Native'}) "
                "SLSsteam may not be installed or configured yet."
            )
        return config_path
    except Exception as e:
        # Graceful fallback: if SteamEnv fails for any reason, use the original native path
        logger.warning(f"get_user_config_path: SteamEnv unavailable ({e}), falling back to native path")
        xdg_config_home_str = os.environ.get("XDG_CONFIG_HOME", "")
        xdg_config_home = (
            Path(xdg_config_home_str).expanduser() if xdg_config_home_str else Path()
        )
        if xdg_config_home_str and Path(xdg_config_home_str).is_absolute():
            config_dir = xdg_config_home / "SLSsteam"
        else:
            config_dir = Path.home() / ".config" / "SLSsteam"
        return config_dir / "config.yaml"


def _get_section_start(content: str, pattern: re.Pattern) -> Optional[int]:
    match = pattern.search(content)
    if not match:
        return None
    section_start = match.end()
    if section_start < len(content) and content[section_start] == "\n":
        section_start += 1
    return section_start


def _get_section_end(
    content: str, section_start: int, next_key_pattern: re.Pattern
) -> int:
    after_section = content[section_start:]
    next_match = next_key_pattern.search(after_section)
    if next_match:
        return section_start + next_match.start()
    return len(content)


def _remove_line_for_match(content: str, match: re.Match) -> str:
    line_start = content.rfind("\n", 0, match.start()) + 1
    if line_start == 0:
        line_start = 0
    line_end = content.find("\n", match.end())
    if line_end == -1:
        line_end = len(content)

    if line_end < len(content) and content[line_end] == "\n":
        line_end += 1

    return content[:line_start] + content[line_end:]


def _remove_matching_entry(
    config_path: Path, pattern: re.Pattern, success_message: str, error_message: str
) -> bool:
    try:
        content = _read_config_content(config_path)
        if content is None:
            return False

        match = pattern.search(content)
        if not match:
            return False

        new_content = _remove_line_for_match(content, match)
        if not _atomic_write(config_path, new_content):
            return False

        logger.info(success_message)
        return True
    except OSError as e:
        logger.error(error_message.format(e=e), exc_info=True)
        return False


def _fix_additional_apps_indentation(content: str) -> Tuple[str, bool]:
    """Fix indentation of AdditionalApps list items."""
    # Find AdditionalApps section
    additional_apps_pattern = re.compile(r"^AdditionalApps:\s*$", re.MULTILINE)
    section_start = _get_section_start(content, additional_apps_pattern)
    if section_start is None:
        return content, False

    # Look for next top-level key
    next_key_pattern = re.compile(r"^[A-Za-z]", re.MULTILINE)
    section_end = _get_section_end(content, section_start, next_key_pattern)

    section_content = content[section_start:section_end]

    # Pattern to find misaligned items: "- item" or "-item"
    misaligned_item_pattern = re.compile(
        r"(^)(\s*)-(\s*)([^\n#]+?)(?=\s*(?:#|$))", re.MULTILINE
    )

    # Fix items by adding 2-space indentation
    fixed_section = misaligned_item_pattern.sub(r"\1  - \4", section_content)

    if fixed_section != section_content:
        fixed_content = content[:section_start] + fixed_section + content[section_end:]
        logger.debug("Fixed indentation of AdditionalApps list items")
        return fixed_content, True

    return content, False


def _get_app_tokens_section(content: str) -> str:
    """Extract the AppTokens section from YAML content."""
    app_tokens_pattern = re.compile(r"^AppTokens:\s*$", re.MULTILINE)
    section_start = _get_section_start(content, app_tokens_pattern)
    if section_start is None:
        return ""

    next_key_pattern = re.compile(r"^[A-Za-z][A-Za-z0-9]*:\s*$", re.MULTILINE)
    section_end = _get_section_end(content, section_start, next_key_pattern)
    return content[section_start:section_end]


def _fix_app_tokens_indentation(content: str) -> Tuple[str, bool]:
    """Fix indentation of AppTokens entries to have 2-space indentation."""
    app_tokens_pattern = re.compile(r"^AppTokens:\s*$", re.MULTILINE)
    section_start = _get_section_start(content, app_tokens_pattern)
    if section_start is None:
        return content, False
    after_section = content[section_start:]

    next_key_pattern = re.compile(r"^[A-Za-z][A-Za-z0-9]*:\s*$", re.MULTILINE)
    next_match = next_key_pattern.search(after_section)

    # Find the last token entry to determine end of section
    last_token_pattern = re.compile(r"^\s*\d+\s*:\s*[^\n]*$", re.MULTILINE)
    last_token_matches = list(last_token_pattern.finditer(after_section))

    if last_token_matches:
        last_token_end = last_token_matches[-1].end()
        newline_after_token = after_section.find("\n", last_token_end)
        if newline_after_token != -1:
            section_end = section_start + newline_after_token + 1
        elif next_match:
            section_end = section_start + next_match.start()
        else:
            section_end = len(content)
    elif next_match:
        section_end = section_start + next_match.start()
    else:
        section_end = len(content)

    section_content = content[section_start:section_end]
    token_pattern = re.compile(r"(^)(\s*)(\d+)(\s*:\s*[^\n]*)", re.MULTILINE)
    fixed_section = token_pattern.sub(r"\1  \3\4", section_content)

    if fixed_section != section_content:
        fixed_content = content[:section_start] + fixed_section + content[section_end:]
        logger.debug("Fixed indentation of AppTokens entries")
        return fixed_content, True

    return content, False


def fix_slssteam_config_indentation(config_path: Path) -> bool:
    """Fix indentation of AdditionalApps and AppTokens entries."""
    try:
        content = _get_config_content_if_enabled(config_path)
        if content is _CONFIG_DISABLED or content is None:
            return False

        fixed_content, mod_apps = _fix_additional_apps_indentation(content)
        fixed_content, mod_tokens = _fix_app_tokens_indentation(fixed_content)

        if mod_apps or mod_tokens:
            if not _atomic_write(config_path, fixed_content):
                return False
            logger.info(f"Fixed indentation in {config_path}")
            return True

        return False

    except OSError as e:
        logger.error(f"Failed to fix indentation in {config_path}: {e}", exc_info=True)
        return False


def _init_config_with_app(config_path: Path, app_id: str, comment: str) -> bool:
    """Create new config file with a single AdditionalApps entry."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if comment:
        new_entry = f"AdditionalApps:\n  - {app_id}   # {comment}\n"
    else:
        new_entry = f"AdditionalApps:\n  - {app_id}\n"

    if _atomic_write(config_path, new_entry):
        logger.info(f"Created config file with AppID '{app_id}' in {config_path}")
        return True
    return False


def _append_to_additional_apps(
    content: str, app_id: str, comment: str, match: re.Match
) -> str:
    """Append AppID to existing AdditionalApps section directly after the last list item."""
    start_pos = match.end()
    remaining = content[start_pos:]
    lines = remaining.split("\n")

    last_item_offset = 0
    curr_offset = 0

    for line in lines:
        line_len = len(line) + 1  # includes \n
        stripped = line.strip()
        if stripped.startswith("-"):
            last_item_offset = curr_offset + line_len
        elif stripped and not stripped.startswith("#") and not line.startswith(" ") and not line.startswith("\t"):
            # Encountered a new top-level YAML section (e.g., DlcData:)
            break
        curr_offset += line_len

    if last_item_offset == 0:
        # AdditionalApps: was empty
        insert_pos = start_pos
        if not content[start_pos:].startswith("\n"):
            new_entry = f"\n  - {app_id}   # {comment}\n" if comment else f"\n  - {app_id}\n"
        else:
            new_entry = f"  - {app_id}   # {comment}\n" if comment else f"  - {app_id}\n"
        return content[:insert_pos] + new_entry + content[insert_pos:]

    insert_pos = start_pos + last_item_offset
    new_entry = f"  - {app_id}   # {comment}\n" if comment else f"  - {app_id}\n"
    return content[:insert_pos] + new_entry + content[insert_pos:]


def add_additional_app(config_path: Path, app_id: str, comment: str = "") -> bool:
    """Add an AppID to the AdditionalApps list in SLSsteam config.yaml."""
    try:
        content = _read_config_content(config_path)
        if content is None:
            return _init_config_with_app(config_path, app_id, comment)

        fixed_content, _ = _fix_additional_apps_indentation(content)

        # Check if AppID already exists
        app_id_pattern = re.compile(
            rf"^\s*-\s*{re.escape(app_id)}\s*(?:#.*)?$", re.MULTILINE
        )
        if app_id_pattern.search(fixed_content):
            logger.debug(f"AppID '{app_id}' already exists in AdditionalApps")
            return False

        additional_apps_pattern = re.compile(r"^AdditionalApps:\s*$", re.MULTILINE)
        match = additional_apps_pattern.search(fixed_content)

        if match:
            new_content = _append_to_additional_apps(
                fixed_content, app_id, comment, match
            )
        else:
            # Create new AdditionalApps section
            if comment:
                entry = f"AdditionalApps:\n  - {app_id}   # {comment}\n"
            else:
                entry = f"AdditionalApps:\n  - {app_id}\n"
            new_content = fixed_content + "\n" + entry

        if not _atomic_write(config_path, new_content):
            return False

        logger.info(f"Added AppID '{app_id}' to AdditionalApps in {config_path}")
        return True

    except OSError as e:
        logger.error(
            f"Failed to add AppID '{app_id}' to {config_path}: {e}",
            exc_info=True,
        )
        return False


def remove_additional_app(config_path: Path, app_id: str) -> bool:
    """Remove an AppID from the AdditionalApps list."""
    app_id_pattern = re.compile(
        rf"^\s*-\s*{re.escape(app_id)}\s*(?:#.*)?$", re.MULTILINE
    )
    return _remove_matching_entry(
        config_path,
        app_id_pattern,
        f"Removed AppID '{app_id}' from AdditionalApps in {config_path}",
        f"Failed to remove AppID '{app_id}': {{e}}",
    )


def add_dlc_data(
    config_path: Path, parent_app_id: str, dlc_id: str, dlc_name: str
) -> bool:
    """Add a DLC entry to DlcData section in SLSsteam config.yaml."""
    try:
        content = _get_config_content_if_enabled(config_path, log_missing=True)
        if content is _CONFIG_DISABLED or content is None:
            return False

        dlc_data_pattern = re.compile(r"^DlcData:\s*$", re.MULTILINE)
        match = dlc_data_pattern.search(content)

        if not match:
            # Create new DlcData section
            new_entry = f'DlcData:\n  {parent_app_id}:\n    {dlc_id}: "{dlc_name}"\n'
            new_content = content + "\n" + new_entry
            return _atomic_write_and_log(
                config_path, new_content, dlc_name, dlc_id, parent_app_id
            )

        dlc_data_end = match.end()

        # Find parent AppID under DlcData
        parent_pattern = re.compile(
            rf"^(\s*){re.escape(parent_app_id)}:\s*$", re.MULTILINE
        )
        parent_match = parent_pattern.search(content, dlc_data_end)

        if not parent_match:
            # Add new parent AppID section under DlcData
            remaining = content[dlc_data_end:]
            next_key_pattern = re.compile(r"^[A-Za-z]", re.MULTILINE)
            next_match = next_key_pattern.search(remaining)
            insert_pos = (
                dlc_data_end + next_match.start() if next_match else len(content)
            )

            new_entry = f'  {parent_app_id}:\n    {dlc_id}: "{dlc_name}"\n'
            new_content = content[:insert_pos] + new_entry + content[insert_pos:]
            return _atomic_write_and_log(
                config_path, new_content, dlc_name, dlc_id, parent_app_id
            )

        # Parent exists, check for DLC
        parent_line_end = parent_match.end()
        parent_indent = len(parent_match.group(1))
        remaining = content[parent_line_end:]

        # Find scope of this parent block
        next_parent_pattern = re.compile(
            rf"^(\s{{{parent_indent}}})[0-9]", re.MULTILINE
        )
        next_match = next_parent_pattern.search(remaining)

        if next_match:
            parent_section = remaining[: next_match.start()]
            insert_pos = parent_line_end + next_match.start()
        else:
            # Until end of DlcData or EOF
            after_dlcdata = content[dlc_data_end:]
            end_match = re.compile(r"^[A-Za-z]", re.MULTILINE).search(after_dlcdata)
            if end_match:
                limit = dlc_data_end + end_match.start() - parent_line_end
                parent_section = remaining[:limit]
                insert_pos = dlc_data_end + end_match.start()
            else:
                parent_section = remaining
                insert_pos = len(content)

        dlc_check_pattern = re.compile(rf'^\s*{re.escape(dlc_id)}:\s*"', re.MULTILINE)
        if dlc_check_pattern.search(parent_section):
            logger.debug(f"DLC '{dlc_id}' already exists under AppID '{parent_app_id}'")
            return False

        # Build new DLC entry with proper indentation
        new_entry = f'{" " * (parent_indent + 2)}{dlc_id}: "{dlc_name}"\n'
        new_content = content[:insert_pos] + new_entry + content[insert_pos:]

        return _atomic_write_and_log(
            config_path, new_content, dlc_name, dlc_id, parent_app_id
        )

    except OSError as e:
        logger.error(f"Failed to add DLC '{dlc_id}': {e}", exc_info=True)
        return False


def _atomic_write_and_log(
    config_path: Path,
    content: str,
    dlc_name: str,
    dlc_id: str,
    parent_app_id: str,
) -> bool:
    """Helper to write file and log success for DLC addition."""
    if not _atomic_write(config_path, content):
        return False
    logger.info(
        f"Added DLC '{dlc_name}' ({dlc_id}) to DlcData under "
        f"AppID '{parent_app_id}' in {config_path}"
    )
    return True


def add_app_token(config_path: Path, app_id: str, token: str) -> bool:
    """Add an AppToken to the AppTokens section in SLSsteam config.yaml."""
    try:
        content = _get_config_content_if_enabled(config_path)
        if content is _CONFIG_DISABLED or content is None:
            return False

        app_tokens_pattern = re.compile(r"^AppTokens:\s*$", re.MULTILINE)
        if not app_tokens_pattern.search(content):
            new_entry = f"AppTokens:\n  {app_id}: {token}\n"
            return _atomic_write(config_path, content + new_entry)

        # Fix indentation FIRST
        fixed_content, _ = _fix_app_tokens_indentation(content)
        content = fixed_content

        # Search for any existing entries for this app_id (with or without quotes)
        dup_pattern = re.compile(
            rf"^ {{2}}['\"]?{re.escape(app_id)}['\"]?\s*:\s*.*(?:\r?\n)?", re.MULTILINE
        )
        
        matches = list(dup_pattern.finditer(content))
        
        if len(matches) == 1:
            match_val_pat = re.compile(
                rf"^ {{2}}['\"]?{re.escape(app_id)}['\"]?\s*:\s*(.+)$", re.MULTILINE
            )
            m = match_val_pat.search(matches[0].group(0))
            if m and m.group(1).strip() == token:
                # Token matches exactly. No update needed.
                return False

        # Remove all existing occurrences of this app_id
        new_content = content
        for m in reversed(matches):
            new_content = new_content[:m.start()] + new_content[m.end():]

        # Insert the single correct entry under AppTokens
        tokens_start = new_content.find("AppTokens:")
        if tokens_start != -1:
            insert_pos = tokens_start + len("AppTokens:")
            if insert_pos < len(new_content) and new_content[insert_pos] == "\n":
                insert_pos += 1
            elif insert_pos < len(new_content) and new_content[insert_pos] == "\r":
                insert_pos += 2
                
            new_token_line = f"  {app_id}: {token}\n"
            new_content = new_content[:insert_pos] + new_token_line + new_content[insert_pos:]
            
            if _atomic_write(config_path, new_content):
                if len(matches) > 1:
                    logger.info(f"Updated AppToken for '{app_id}' and removed duplicates")
                elif len(matches) == 1:
                    logger.info(f"Updated AppToken for '{app_id}'")
                else:
                    logger.info(f"Added AppToken for '{app_id}'")
                return True
        return False
    except OSError as e:
        logger.error(f"Failed to add AppToken '{app_id}': {e}", exc_info=True)
        return False


def _section_bounds(content: str, section_name: str) -> Optional[Tuple[int, int]]:
    """Return content offsets for a top-level YAML section's body."""
    match = re.search(rf"^{re.escape(section_name)}:\s*$", content, re.MULTILINE)
    if not match:
        return None
    body_start = match.end()
    if body_start < len(content) and content[body_start] == "\n":
        body_start += 1
    next_match = re.search(r"^[A-Za-z][A-Za-z0-9_]*:\s*.*$", content[body_start:], re.MULTILINE)
    body_end = body_start + next_match.start() if next_match else len(content)
    return body_start, body_end


def _yaml_scalar(value: str, quote: bool = False) -> str:
    value = str(value)
    if quote:
        return '"' + value.replace('"', '\\"') + '"'
    return value


def _upsert_mapping_entries(
    content: str, section_name: str, entries: Dict[str, str], quote_values: bool = False
) -> Tuple[str, bool]:
    """Upsert two-space mapping entries while retaining section comments."""
    if not entries:
        return content, False
    bounds = _section_bounds(content, section_name)
    if bounds is None:
        block = f"\n{section_name}:\n" + "".join(
            f"  {key}: {_yaml_scalar(value, quote_values)}\n" for key, value in entries.items()
        )
        return content.rstrip("\n") + block, True

    start, end = bounds
    section = content[start:end]
    changed = False
    for key, value in entries.items():
        pattern = re.compile(rf"^([ \t]*)['\"]?{re.escape(str(key))}['\"]?\s*:\s*[^\n]*(?:\n|$)", re.MULTILINE)
        replacement = f"  {key}: {_yaml_scalar(value, quote_values)}\n"
        if pattern.search(section):
            new_section, count = pattern.subn(replacement, section, count=1)
            changed = changed or new_section != section
            section = new_section
        else:
            insert_at = len(section)
            section = section[:insert_at] + replacement + section[insert_at:]
            changed = True
    return content[:start] + section + content[end:], changed


def _upsert_list_entries(content: str, section_name: str, values: List[str]) -> Tuple[str, bool]:
    if not values:
        return content, False
    bounds = _section_bounds(content, section_name)
    if bounds is None:
        block = f"\n{section_name}:\n" + "".join(f"  - {value}\n" for value in values)
        return content.rstrip("\n") + block, True
    start, end = bounds
    section = content[start:end]
    existing = set(re.findall(r"^\s*-\s*([^\s#]+)", section, re.MULTILINE))
    missing = [str(value) for value in values if str(value) not in existing]
    if not missing:
        return content, False
    return content[:start] + section + "".join(f"  - {value}\n" for value in missing) + content[end:], True


def configure_native_manifest_source(
    config_path: Path,
    appid: str,
    game_name: str = "",
    manifest_ids: Optional[Dict[str, str]] = None,
    decryption_keys: Optional[Dict[str, str]] = None,
    app_token: str = "",
) -> bool:
    """Atomically configure ManifestIds, keys, token, and depot injection for WUDRM."""
    if not appid or not str(appid).isdigit():
        return False
    content = _get_config_content_if_enabled(config_path)
    if content is _CONFIG_DISABLED or content is None:
        return False

    changed = False
    content, did_change = _upsert_mapping_entries(
        content, "ManifestIds", manifest_ids or {}, quote_values=False
    )
    changed = changed or did_change
    content, did_change = _upsert_mapping_entries(
        content, "DecryptionKeys", decryption_keys or {}, quote_values=True
    )
    changed = changed or did_change
    content, did_change = _upsert_list_entries(
        content, "AdditionalDepots", list((manifest_ids or {}).keys())
    )
    changed = changed or did_change

    if app_token:
        content, did_change = _upsert_mapping_entries(
            content, "AppTokens", {str(appid): app_token}, quote_values=False
        )
        changed = changed or did_change

    if changed and _atomic_write(config_path, content):
        logger.info(
            "Configured native manifest source for AppID %s (%d manifest IDs, %d keys)%s",
            appid,
            len(manifest_ids or {}),
            len(decryption_keys or {}),
            f" ({game_name})" if game_name else "",
        )
        return True
    # An already matching configuration is still successfully configured;
    # callers must not fall back to a network provider merely because there
    # was nothing to rewrite.
    return not changed

def get_app_tokens(config_path: Path) -> Dict[str, str]:
    """Get all AppTokens from SLSsteam config.yaml."""
    tokens = {}
    try:
        if not config_path.exists():
            return tokens

        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        section_content = _get_app_tokens_section(content)
        token_pattern = re.compile(r"^\s*(\d+)\s*:\s*(.+)$", re.MULTILINE)

        for token_match in token_pattern.finditer(section_content):
            app_id = token_match.group(1).strip()
            token = token_match.group(2).strip()
            tokens[app_id] = token

    except OSError as e:
        logger.error(f"Failed to read AppTokens from {config_path}: {e}", exc_info=True)

    return tokens


def remove_app_token(config_path: Path, app_id: str) -> bool:
    """Remove an AppID entry from the AppTokens section in SLSsteam config.yaml."""
    app_id_pattern = re.compile(
        rf"^\s*{re.escape(app_id)}\s*:\s*\S+" r"(?:\s*#.*)?$",
        re.MULTILINE,
    )
    return _remove_matching_entry(
        config_path,
        app_id_pattern,
        f"Removed AppID '{app_id}' from AppTokens in {config_path}",
        f"Failed to remove AppToken for '{app_id}': {{e}}",
    )


def get_fake_app_ids(config_path: Path, fake_appid: str = "") -> Set[str]:
    """Get all FakeAppIds from SLSsteam config.yaml."""
    fake_app_ids = set()

    if not fake_appid:
        fake_appid = get_fake_appid_for_online()

    try:
        if not config_path.exists():
            return fake_app_ids

        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        fake_appids_pattern = re.compile(r"^FakeAppIds:\s*$", re.MULTILINE)
        match = fake_appids_pattern.search(content)

        if not match:
            return fake_app_ids

        section_start = match.end()
        after_section = content[section_start:]
        next_key_pattern = re.compile(r"^[A-Za-z]", re.MULTILINE)
        next_match = next_key_pattern.search(after_section)

        if next_match:
            section_end = section_start + next_match.start()
        else:
            section_end = len(content)

        section_content = content[section_start:section_end]
        entry_pattern = re.compile(
            rf"^\s*(\d+)\s*:\s*{re.escape(fake_appid)}", re.MULTILINE
        )

        for entry_match in entry_pattern.finditer(section_content):
            app_id = entry_match.group(1).strip()
            fake_app_ids.add(app_id)

    except OSError as e:
        logger.error(
            f"Failed to read FakeAppIds from {config_path}: {e}",
            exc_info=True,
        )

    return fake_app_ids


def get_fake_appid(config_path: Path, app_id: str) -> Optional[str]:
    """Get the FakeAppId for a specific AppID from SLSsteam config.yaml."""
    try:
        if not config_path.exists():
            return None

        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        fake_appids_pattern = re.compile(r"^FakeAppIds:\s*$", re.MULTILINE)
        match = fake_appids_pattern.search(content)

        if not match:
            return None

        section_start = match.end()
        after_section = content[section_start:]
        next_key_pattern = re.compile(r"^[A-Za-z]", re.MULTILINE)
        next_match = next_key_pattern.search(after_section)

        if next_match:
            section_end = section_start + next_match.start()
        else:
            section_end = len(content)

        section_content = content[section_start:section_end]
        entry_pattern = re.compile(
            rf"^\s*{re.escape(app_id)}\s*:\s*(\d+)", re.MULTILINE
        )

        entry_match = entry_pattern.search(section_content)
        if entry_match:
            return entry_match.group(1).strip()

    except OSError as e:
        logger.error(
            f"Failed to read FakeAppId for '{app_id}' from {config_path}: {e}",
            exc_info=True,
        )

    return None


def add_fake_app_id(
    config_path: Path,
    app_id: str,
    game_name: str = "",
    fake_appid: str = "",
) -> bool:
    """Add an AppID to the FakeAppIds list in SLSsteam config.yaml."""
    if not fake_appid:
        fake_appid = get_fake_appid_for_online()

    suffix = "Spacewar" if fake_appid == "480" else "SLSonline"

    try:
        content = _get_config_content_if_enabled(config_path)
        if content is _CONFIG_DISABLED:
            return False
        if content is None:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            entry = f"FakeAppIds:\n  {app_id}: {fake_appid}"
            if game_name:
                entry += f"  # {game_name} -> {suffix}\n"
            else:
                entry += "\n"
            return _atomic_write(config_path, entry)

        existing_pattern = re.compile(
            rf"^\s*{re.escape(app_id)}\s*:\s*{re.escape(fake_appid)}",
            re.MULTILINE,
        )

        if existing_pattern.search(content):
            return False

        fake_appids_pattern = re.compile(r"^FakeAppIds:\s*$", re.MULTILINE)
        match = fake_appids_pattern.search(content)

        if match:
            # Append to existing section
            section_start = match.end()
            if section_start < len(content) and content[section_start] == "\n":
                section_start += 1
            remaining = content[section_start:]
            lines = remaining.split("\n")

            last_entry_end = section_start
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and stripped[0].isdigit():
                    last_entry_end = section_start + sum(
                        len(lines[j]) + 1 for j in range(i + 1)
                    )
                elif not stripped or stripped.startswith("#"):
                    continue
                else:
                    break
            else:
                last_entry_end = len(content)

            insert_pos = last_entry_end
            entry = f"  {app_id}: {fake_appid}"
            if game_name:
                entry += f"  # {game_name} -> {suffix}\n"
            else:
                entry += "\n"

            new_content = content[:insert_pos] + entry + content[insert_pos:]
        else:
            entry = f"FakeAppIds:\n  {app_id}: {fake_appid}"
            if game_name:
                entry += f"  # {game_name} -> {suffix}\n"
            else:
                entry += "\n"
            new_content = content + "\n" + entry

        if not _atomic_write(config_path, new_content):
            return False

        logger.info(f"Added AppID '{app_id}' to FakeAppIds in {config_path}")
        return True

    except OSError as e:
        logger.error(f"Failed to add FakeAppId '{app_id}': {e}", exc_info=True)
        return False


def remove_fake_app_id(config_path: Path, app_id: str, fake_appid: str = "") -> bool:
    """Remove an AppID from the FakeAppIds list in SLSsteam config.yaml."""
    if fake_appid:
        app_id_pattern = re.compile(
            rf"^\s*{re.escape(app_id)}\s*:\s*{re.escape(fake_appid)}" r"(?:\s*#.*)?$",
            re.MULTILINE,
        )
    else:
        # Match any fake_appid entry for this app_id
        app_id_pattern = re.compile(
            rf"^\s*{re.escape(app_id)}\s*:\s*\S+" r"(?:\s*#.*)?$",
            re.MULTILINE,
        )
    return _remove_matching_entry(
        config_path,
        app_id_pattern,
        f"Removed AppID '{app_id}' from FakeAppIds in {config_path}",
        f"Failed to remove FakeAppId '{app_id}': {{e}}",
    )


def check_and_merge_fakeappid_db(config_path: Path) -> bool:
    """Check if fakeappid database integration is enabled and merge it if so.

    Returns:
        True if changes were written, False otherwise.
    """
    settings = get_settings()
    if not settings.value("fakeappid_db_integration", False, type=bool):
        return False

    if not is_slssteam_mode_enabled():
        return False

    if not is_slssteam_config_management_enabled():
        return False

    # Get database file path
    from utils.paths import Paths
    db_path = Paths.resource("fakeapps_accela.yaml")
    if not db_path.exists():
        logger.warning(f"Fake AppID database not found at {db_path}")
        return False

    # Parse database FakeAppIds
    db_fakeapps = {}
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line == "FakeAppIds:":
                    continue
                # Split at comment if any
                comment = ""
                if "#" in line:
                    line, comment = line.split("#", 1)
                    comment = comment.strip()
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()
                    if k.isdigit() and v.isdigit():
                        db_fakeapps[k] = (v, comment)
    except Exception as e:
        logger.error(f"Failed to parse Fake AppID database: {e}")
        return False

    if not db_fakeapps:
        return False

    # Load current content
    try:
        content = _read_config_content(config_path)
        if content is None:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            content = ""
    except OSError as e:
        logger.error(f"Failed to read config file {config_path}: {e}")
        return False

    # Find FakeAppIds section
    fake_appids_pattern = re.compile(r"^FakeAppIds:\s*$", re.MULTILINE)
    match = fake_appids_pattern.search(content)

    # Let's collect existing FakeAppIds
    existing_fake_apps = {}
    if match:
        section_start = match.end()
        after_section = content[section_start:]
        next_key_pattern = re.compile(r"^[A-Za-z]", re.MULTILINE)
        next_match = next_key_pattern.search(after_section)
        section_end = section_start + next_match.start() if next_match else len(content)
        section_content = content[section_start:section_end]
        
        entry_pattern = re.compile(r"^\s*(\d+)\s*:\s*(\d+)", re.MULTILINE)
        for m in entry_pattern.finditer(section_content):
            existing_fake_apps[m.group(1).strip()] = m.group(2).strip()

    # Determine which entries are missing
    missing_entries = {}
    for appid, (fake_appid, comment) in db_fakeapps.items():
        if appid not in existing_fake_apps:
            missing_entries[appid] = (fake_appid, comment)

    if not missing_entries:
        logger.debug("No missing FakeAppIds to merge.")
        return False

    logger.info(f"Merging {len(missing_entries)} entries from database into SLSsteam FakeAppIds...")
    
    # Create the text block to insert
    insert_text = ""
    for appid, (fake_appid, comment) in missing_entries.items():
        comment_suffix = f"  # {comment}" if comment else ""
        insert_text += f"  {appid}: {fake_appid}{comment_suffix}\n"

    new_content = ""
    if match:
        # Find where to insert. We insert right after "FakeAppIds:\n"
        insert_pos = match.end()
        if insert_pos < len(content) and content[insert_pos] == "\n":
            insert_pos += 1
        new_content = content[:insert_pos] + insert_text + content[insert_pos:]
    else:
        # Section doesn't exist, append it
        new_content = content.rstrip() + "\n\nFakeAppIds:\n" + insert_text

    # Write atomically
    _create_backup(config_path)
    if _atomic_write(config_path, new_content):
        logger.info(f"Successfully merged Fake AppID database into {config_path}")
        return True
    return False


def clean_fakeappid_db(config_path: Path) -> bool:
    """Remove all FakeAppIds that belong to the database from SLSsteam config.yaml.

    Returns:
        True if changes were written, False otherwise.
    """
    if not config_path.exists():
        return False

    from utils.paths import Paths
    db_path = Paths.resource("fakeapps_accela.yaml")
    if not db_path.exists():
        return False

    # Parse database AppIDs
    db_appids = set()
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line == "FakeAppIds:":
                    continue
                if "#" in line:
                    line, _ = line.split("#", 1)
                if ":" in line:
                    k, _ = line.split(":", 1)
                    k = k.strip()
                    if k.isdigit():
                        db_appids.add(k)
    except Exception as e:
        logger.error(f"Failed to parse Fake AppID database: {e}")
        return False

    if not db_appids:
        return False

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        logger.error(f"Failed to read config file {config_path}: {e}")
        return False

    # Find FakeAppIds section
    fake_appids_pattern = re.compile(r"^FakeAppIds:\s*$", re.MULTILINE)
    match = fake_appids_pattern.search(content)
    if not match:
        return False

    section_start = match.end()
    after_section = content[section_start:]
    next_key_pattern = re.compile(r"^[A-Za-z]", re.MULTILINE)
    next_match = next_key_pattern.search(after_section)
    section_end = section_start + next_match.start() if next_match else len(content)
    section_content = content[section_start:section_end]

    # Rebuild section content, omitting any lines that match db_appids
    new_section_lines = []
    removed_count = 0
    entry_pattern = re.compile(r"^\s*(\d+)\s*:")
    for line in section_content.split("\n"):
        m = entry_pattern.match(line)
        if m:
            appid = m.group(1).strip()
            if appid in db_appids:
                removed_count += 1
                continue  # skip/remove this line
        new_section_lines.append(line)

    if removed_count == 0:
        return False

    new_section_content = "\n".join(new_section_lines)
    new_content = content[:section_start] + new_section_content + content[section_end:]

    _create_backup(config_path)
    if _atomic_write(config_path, new_content):
        logger.info(f"Successfully cleaned {removed_count} database FakeAppIds from {config_path}")
        return True
    return False


def get_denuvo_games(config_path: Path) -> Dict[str, List[str]]:
    """Get all DenuvoGames mappings from SLSsteam config.yaml.

    Returns:
        Dict mapping SteamID to list of AppIDs.
    """
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        logger.error(f"Failed to read config file {config_path}: {e}")
        return {}

    # Find DenuvoGames section
    denuvo_games_pattern = re.compile(r"^DenuvoGames:\s*$", re.MULTILINE)
    match = denuvo_games_pattern.search(content)
    if not match:
        return {}

    section_start = match.end()
    after_section = content[section_start:]
    next_key_pattern = re.compile(r"^[A-Za-z]", re.MULTILINE)
    next_match = next_key_pattern.search(after_section)
    section_end = section_start + next_match.start() if next_match else len(content)
    section_content = content[section_start:section_end]

    res = {}
    current_steam_id = None

    for line in section_content.split("\n"):
        line_strip = line.strip()
        if not line_strip or line_strip.startswith("#"):
            continue

        steam_id_match = re.match(r"^\s*['\"]?(\d+)['\"]?:\s*$", line)
        if steam_id_match:
            current_steam_id = steam_id_match.group(1)
            res[current_steam_id] = []
            continue

        appid_match = re.match(r"^\s*-\s*['\"]?(\d+)['\"]?\s*(?:#.*)?$", line)
        if appid_match and current_steam_id is not None:
            res[current_steam_id].append(appid_match.group(1))

    return res


def save_denuvo_games(config_path: Path, steam_id: str, appids: List[str]) -> bool:
    """Deprecated: Denuvo status should never be written to SLS config. Calls clean_denuvo_games_section instead."""
    return clean_denuvo_games_section(config_path)


def clean_denuvo_games_section(config_path: Path) -> bool:
    """
    Remove all entries under DenuvoGames in SLSsteam config.yaml, returning it to an empty block.
    This reverses the unintentional Denuvo blocklist write introduced in v2.5.4.
    """
    if not config_path.exists():
        return False
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        logger.error(f"Failed to read config file {config_path}: {e}")
        return False

    denuvo_games_pattern = re.compile(r"^DenuvoGames:\s*$", re.MULTILINE)
    match = denuvo_games_pattern.search(content)
    if not match:
        return False

    section_start = match.end()
    after_section = content[section_start:]
    next_key_pattern = re.compile(r"^[A-Za-z]", re.MULTILINE)
    next_match = next_key_pattern.search(after_section)
    section_end = section_start + next_match.start() if next_match else len(content)

    section_content = content[section_start:section_end]
    # If there is content (indented keys or appids) under DenuvoGames, strip it
    if section_content.strip():
        new_content = content[:section_start] + "\n" + content[section_end:]
        _create_backup(config_path)
        if _atomic_write(config_path, new_content):
            logger.info(f"Successfully cleaned DenuvoGames block in {config_path}")
            return True
    return False
