import configparser
import logging

from utils.paths import Paths

logger = logging.getLogger(__name__)

# Module-level singleton cache — depots.ini is a static bundled file that never
# changes during a session.  Parsing 146K entries on every zip processed is
# wasteful; cache the result after the first read.
_depot_cache: dict | None = None


def parse_depots_ini():
    global _depot_cache
    if _depot_cache is not None:
        return _depot_cache

    config = configparser.ConfigParser()
    depot_descriptions = {}

    ini_path = Paths.resource("depots.ini")

    try:
        if not ini_path.exists():
            logger.warning(
                f"'depots.ini' file not found at {str(ini_path)}. Depot names may be generic."
            )
            _depot_cache = {}
            return _depot_cache

        config.read(str(ini_path), encoding="utf-8")

        if "depots" in config:
            for depot_id, name in config["depots"].items():
                depot_descriptions[depot_id] = name
            logger.debug(
                f"Successfully loaded {len(depot_descriptions)} depot descriptions from .ini."
            )
        else:
            logger.warning(f"No [depots] section found in '{str(ini_path)}'.")

    except configparser.Error as e:
        logger.error(f"Failed to parse 'depots.ini' at {str(ini_path)}: {e}")
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while reading 'depots.ini': {e}",
            exc_info=True,
        )

    _depot_cache = depot_descriptions
    return _depot_cache
