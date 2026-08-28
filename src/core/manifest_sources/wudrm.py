from __future__ import annotations

from pathlib import Path

from core.manifest_sources.base import ManifestSourceError
from core.manifest_sources.models import ManifestSourceResult


def configure_wudrm_native(
    result: ManifestSourceResult, config_path: Path | None = None
) -> bool:
    """Configure SLSsteam's download.lua inputs for native Steam retrieval.

    WUDRM supplies a Manifest Request Code for each GID; it does not return raw
    depot manifest bytes, so this function deliberately only configures the
    native SLSsteam path.
    """
    if not result.native_ready:
        raise ManifestSourceError(
            "wudrm",
            "Lua source needs a manifest GID and 64-character depot key for every depot",
        )
    from utils.yaml_config_manager import (
        configure_native_manifest_source,
        get_user_config_path,
    )

    target = Path(config_path) if config_path else get_user_config_path()
    return configure_native_manifest_source(
        target,
        appid=result.appid,
        game_name=result.game_name,
        manifest_ids=result.manifest_gids,
        decryption_keys=result.depot_keys,
        app_token=result.app_token,
    )
