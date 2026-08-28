from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from core.manifest_sources.models import ManifestSourceResult
from utils.helpers import get_base_path


class ManifestSourceCache:
    """Source-aware metadata index; existing Hubcap ZIP locations remain compatible."""

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root else get_base_path() / "manifest_sources"

    def record(self, result: ManifestSourceResult) -> Path:
        target_dir = self.root / result.source
        target_dir.mkdir(parents=True, exist_ok=True)
        suffix = "" if result.branch == "public" else f"_{result.branch}"
        target = target_dir / f"{result.appid}{suffix}.json"
        data = result.to_cache_dict()
        data["cached_at"] = int(time.time())
        target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return target

    def metadata_path(self, source: str, appid: str, branch: str = "public") -> Path:
        suffix = "" if branch == "public" else f"_{branch}"
        return self.root / source / f"{appid}{suffix}.json"
