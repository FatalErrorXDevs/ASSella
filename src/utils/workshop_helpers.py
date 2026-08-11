import os
import re
import shutil
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def strip_emojis(text: str) -> str:
    """Remove emoji and non-standard symbol characters from strings while preserving brackets and ASCII symbols."""
    if not text:
        return ""
    # Correct unicode emoji regex pattern
    emoji_pattern = re.compile(
        "["
        "\U00010000-\U0010FFFF"
        "\u2600-\u26FF"
        "\u2700-\u27BF"
        "]+",
        flags=re.UNICODE,
    )
    clean = emoji_pattern.sub("", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean or clean in (".", "'", '"', "-"):
        return text.strip()
    return clean


def fetch_workshop_details(publishedfileids: List[str]) -> Dict[str, dict]:
    """Fetch workshop item titles, updated timestamps, and file sizes.
    Uses WorkshopCacheManager (SQLite) first for instant cached results,
    and queries Steam Web API only for missing/uncached items.
    """
    if not publishedfileids:
        return {}

    str_wids = [str(w) for w in publishedfileids]
    
    # 1. Read from SQLite Workshop Cache
    try:
        from utils.workshop_cache import WorkshopCacheManager
        cache_mgr = WorkshopCacheManager()
        cached_results = cache_mgr.get_cached_details(str_wids)
    except Exception as e:
        logger.debug(f"Workshop cache lookup error: {e}")
        cache_mgr = None
        cached_results = {}

    missing_wids = [w for w in str_wids if w not in cached_results]
    if not missing_wids:
        return cached_results

    # 2. Query Steam Web API for missing item IDs
    url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
    data = {"itemcount": len(missing_wids)}
    for i, wid in enumerate(missing_wids):
        data[f"publishedfileids[{i}]"] = wid

    fresh_results = {}
    try:
        res = requests.post(url, data=data, timeout=10)
        if res.status_code == 200:
            payload = res.json()
            items = payload.get("response", {}).get("publishedfiledetails", [])
            for item in items:
                wid_str = str(item.get("publishedfileid", ""))
                if wid_str:
                    raw_title = item.get("title", f"Workshop Item #{wid_str}")
                    fresh_results[wid_str] = {
                        "title": raw_title or f"Workshop Item #{wid_str}",
                        "time_updated": int(item.get("time_updated", 0)),
                        "file_size": int(item.get("file_size", 0)),
                    }
            if cache_mgr and fresh_results:
                cache_mgr.upsert_details(fresh_results)
    except Exception as e:
        logger.debug(f"Failed to fetch workshop item details from Steam API: {e}")

    # Combine cached + fresh results
    return {**cached_results, **fresh_results}


def delete_workshop_item(appid: str, wid: str, mod_path: str) -> bool:
    """Delete a local workshop item directory and clean up manifest entries."""
    success = False
    try:
        # 1. Delete content directory
        if mod_path and os.path.exists(mod_path):
            shutil.rmtree(mod_path, ignore_errors=True)
            logger.info(f"Deleted workshop item directory for WID {wid} at {mod_path}")
            success = True

        # 2. Check and clean up appworkshop_<appid>.acf if present
        from core.steam_helpers import get_steam_libraries
        for lib in get_steam_libraries():
            acf_path = os.path.join(lib, "steamapps", "workshop", f"appworkshop_{appid}.acf")
            if os.path.exists(acf_path):
                try:
                    with open(acf_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    # Remove block for wid
                    pattern = re.compile(rf'"{wid}"\s*\{{[^}}]*\}}', re.DOTALL)
                    new_content = pattern.sub("", content)
                    if new_content != content:
                        with open(acf_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        logger.info(f"Cleaned up WID {wid} from {acf_path}")
                except Exception as acf_err:
                    logger.debug(f"Failed to clean up workshop acf {acf_path}: {acf_err}")

            # 3. Clean up downloads folder if present
            dl_dir = os.path.join(lib, "steamapps", "workshop", "downloads", str(appid), str(wid))
            if os.path.exists(dl_dir):
                shutil.rmtree(dl_dir, ignore_errors=True)

    except Exception as e:
        logger.error(f"Failed to delete workshop item {wid}: {e}")

    return success
