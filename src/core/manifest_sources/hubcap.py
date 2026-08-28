from __future__ import annotations

from pathlib import Path

from core.manifest_sources.base import ManifestSource, ManifestSourceError
from core.manifest_sources.models import (
    ManifestCapability,
    ManifestRequest,
    ManifestSourceResult,
)


class HubcapSource(ManifestSource):
    name = "hubcap"
    capabilities = (
        ManifestCapability.METADATA
        | ManifestCapability.RAW_MANIFEST
        | ManifestCapability.RAW_BUNDLE
        | ManifestCapability.SEARCH
        | ManifestCapability.FRESHNESS
    )

    def available(self, request: ManifestRequest) -> bool:
        from core.morrenus_api import _get_headers

        return _get_headers() is not None

    def resolve(self, request: ManifestRequest) -> ManifestSourceResult:
        from core.morrenus_api import download_manifest

        path, error = download_manifest(request.appid, branch=request.branch)
        if error or not path:
            raise ManifestSourceError(self.name, error or "manifest download returned no file")
        return ManifestSourceResult(
            appid=request.appid,
            source=self.name,
            branch=request.branch,
            raw_bundle_path=Path(path),
            provenance={"endpoint": "manifest"},
        )

    def generate_bundle(self, request: ManifestRequest) -> ManifestSourceResult:
        from core.morrenus_api import generate_bundle_manifest

        payload, error = generate_bundle_manifest(request.appid, branch=request.branch)
        if error or not payload:
            raise ManifestSourceError(self.name, error or "bundle generation returned no data")
        return ManifestSourceResult(
            appid=request.appid,
            source=self.name,
            branch=request.branch,
            raw_bundle_bytes=payload,
            provenance={"endpoint": "generate/appmanifest"},
        )
