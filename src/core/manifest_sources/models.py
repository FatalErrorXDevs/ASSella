from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Flag, auto
from pathlib import Path
from typing import Any, Dict, Optional


class ManifestCapability(Flag):
    """Capabilities exposed by a manifest source."""

    METADATA = auto()
    NATIVE_STEAM = auto()
    RAW_MANIFEST = auto()
    RAW_BUNDLE = auto()
    SEARCH = auto()
    FRESHNESS = auto()


@dataclass(frozen=True)
class ManifestRequest:
    appid: str
    branch: str = "public"
    lua_path: Optional[Path] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "appid", str(self.appid).strip())
        object.__setattr__(self, "branch", str(self.branch or "public").strip())
        if not self.appid.isdigit():
            raise ValueError("AppID must contain digits only")


@dataclass
class DepotManifest:
    depot_id: str
    manifest_gid: str = ""
    depot_key: str = ""
    size: int = 0
    oslist: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        self.depot_id = str(self.depot_id)
        self.manifest_gid = str(self.manifest_gid or "")
        self.depot_key = str(self.depot_key or "")
        try:
            self.size = int(self.size or 0)
        except (TypeError, ValueError):
            self.size = 0


@dataclass
class ManifestSourceResult:
    appid: str
    source: str
    branch: str = "public"
    game_name: str = ""
    installdir: str = ""
    buildid: str = ""
    app_token: str = ""
    depots: Dict[str, DepotManifest] = field(default_factory=dict)
    raw_bundle_path: Optional[Path] = None
    raw_bundle_bytes: Optional[bytes] = field(default=None, repr=False)
    native_ready: bool = False
    provenance: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.appid = str(self.appid)
        self.branch = str(self.branch or "public")
        self.buildid = str(self.buildid or "")
        self.depots = {
            str(depot_id): (
                value
                if isinstance(value, DepotManifest)
                else DepotManifest(depot_id=str(depot_id), **value)
            )
            for depot_id, value in self.depots.items()
        }

    @property
    def manifest_gids(self) -> Dict[str, str]:
        return {
            depot_id: depot.manifest_gid
            for depot_id, depot in self.depots.items()
            if depot.manifest_gid
        }

    @property
    def depot_keys(self) -> Dict[str, str]:
        return {
            depot_id: depot.depot_key
            for depot_id, depot in self.depots.items()
            if depot.depot_key
        }

    def to_game_data(self) -> Dict[str, Any]:
        """Return the legacy game_data shape used by existing download tasks."""
        return {
            "appid": self.appid,
            "game_name": self.game_name or f"App {self.appid}",
            "installdir": self.installdir,
            "buildid": self.buildid,
            "branch": self.branch,
            "app_token": self.app_token,
            "manifest_source": self.source,
            "native_manifest_source": self.native_ready,
            "manifests": self.manifest_gids,
            "depots": {
                depot_id: {
                    "key": depot.depot_key,
                    "size": str(depot.size),
                    "oslist": depot.oslist,
                    "desc": depot.description or f"Depot {depot_id}",
                }
                for depot_id, depot in self.depots.items()
            },
        }

    def to_cache_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop("raw_bundle_bytes", None)
        if self.raw_bundle_path:
            data["raw_bundle_path"] = str(self.raw_bundle_path)
        return data
