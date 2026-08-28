from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from core.manifest_sources.base import ManifestSource, ManifestSourceError
from core.manifest_sources.models import (
    DepotManifest,
    ManifestCapability,
    ManifestRequest,
    ManifestSourceResult,
)
from utils.helpers import get_base_path


class LocalLuaSource(ManifestSource):
    name = "local_lua"
    capabilities = ManifestCapability.METADATA | ManifestCapability.NATIVE_STEAM

    def __init__(self, lua_dir: Optional[Path] = None, enrich_from_steam: bool = True):
        self.lua_dir = Path(lua_dir) if lua_dir else get_base_path() / "cached_luas"
        self.enrich_from_steam = enrich_from_steam

    def _path_for(self, request: ManifestRequest) -> Path:
        return Path(request.lua_path) if request.lua_path else self.lua_dir / f"{request.appid}.lua"

    def available(self, request: ManifestRequest) -> bool:
        return self._path_for(request).is_file()

    @staticmethod
    def parse_text(text: str, source_path: Optional[Path] = None) -> ManifestSourceResult:
        matches = list(re.finditer(r"addappid\((.*?)\)(.*)", text, re.IGNORECASE))
        if not matches:
            raise ManifestSourceError("local_lua", "no addappid entries found")

        root = matches.pop(0)
        root_args = [part.strip().strip("\"'") for part in root.group(1).split(",")]
        appid = root_args[0] if root_args else ""
        if not appid.isdigit():
            raise ManifestSourceError("local_lua", "invalid or missing AppID")

        name_match = re.search(r"--\s*(.*)", root.group(2))
        game_name = name_match.group(1).strip() if name_match else f"App {appid}"
        depots = {}
        for match in matches:
            args = [part.strip().strip("\"'") for part in match.group(1).split(",")]
            if not args or not args[0].isdigit():
                continue
            depot_id = args[0]
            # addappid(appid) entries are DLC/app references, not depots.
            # Depot entries carry the AES key as their third argument.
            if len(args) <= 2 or not args[2]:
                continue
            key = args[2]
            depot_name_match = re.search(r"--\s*(.*)", match.group(2))
            depots[depot_id] = DepotManifest(
                depot_id=depot_id,
                depot_key=key,
                description=(
                    depot_name_match.group(1).strip()
                    if depot_name_match
                    else f"Depot {depot_id}"
                ),
            )

        for match in re.finditer(
            r"setManifestid\(\s*(\d+)\s*,\s*[\"'](\d+)[\"'](?:\s*,\s*(\d+))?",
            text,
            re.IGNORECASE,
        ):
            depot_id, gid, size = match.groups()
            depot = depots.setdefault(depot_id, DepotManifest(depot_id=depot_id))
            depot.manifest_gid = gid
            depot.size = int(size or 0)

        token_match = re.search(
            r"addtoken\(\s*\d+\s*,\s*[\"']([^\"']+)[\"']", text, re.IGNORECASE
        )
        result = ManifestSourceResult(
            appid=appid,
            source="local_lua",
            game_name=game_name,
            app_token=token_match.group(1) if token_match else "",
            depots=depots,
            native_ready=bool(depots) and all(
                re.fullmatch(r"\d+", depot.manifest_gid)
                and re.fullmatch(r"[0-9a-fA-F]{64}", depot.depot_key)
                for depot in depots.values()
            ),
            provenance={"lua_path": str(source_path) if source_path else ""},
        )
        return result

    @classmethod
    def parse_path(cls, lua_path: Path) -> ManifestSourceResult:
        path = Path(lua_path)
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            raise ManifestSourceError("local_lua", f"cannot read {path}: {exc}") from exc
        return cls.parse_text(text, source_path=path)

    def _enrich(self, result: ManifestSourceResult, branch: str) -> None:
        if not self.enrich_from_steam:
            return
        try:
            from core.steam_api import get_depot_info_from_api

            info = get_depot_info_from_api(int(result.appid)) or {}
        except Exception:
            return

        result.game_name = info.get("name") or result.game_name
        result.installdir = info.get("installdir") or result.installdir
        result.buildid = str(info.get("buildid") or result.buildid)
        for depot_id, depot_info in (info.get("depots") or {}).items():
            if not isinstance(depot_info, dict):
                continue
            depot = result.depots.get(str(depot_id))
            if not depot:
                continue
            depot.oslist = str(depot_info.get("oslist") or depot.oslist)
            depot.description = str(depot_info.get("name") or depot.description)
            try:
                depot.size = int(depot_info.get("size") or depot.size)
            except (TypeError, ValueError):
                pass

    def resolve(self, request: ManifestRequest) -> ManifestSourceResult:
        path = self._path_for(request)
        if not path.is_file():
            raise ManifestSourceError(self.name, f"Lua file not found for AppID {request.appid}")
        result = self.parse_path(path)
        if result.appid != request.appid:
            raise ManifestSourceError(
                self.name,
                f"Lua AppID {result.appid} does not match requested AppID {request.appid}",
            )
        result.branch = request.branch
        self._enrich(result, request.branch)
        return result
