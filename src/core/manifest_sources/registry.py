from __future__ import annotations

from typing import Iterable, List, Optional

from core.manifest_sources.base import ManifestSource, ManifestSourceError
from core.manifest_sources.cache import ManifestSourceCache
from core.manifest_sources.models import (
    ManifestCapability,
    ManifestRequest,
    ManifestSourceResult,
)


class ManifestSourceRegistry:
    def __init__(
        self,
        sources: Optional[Iterable[ManifestSource]] = None,
        cache: Optional[ManifestSourceCache] = None,
    ):
        self.sources: List[ManifestSource] = list(sources or [])
        self.cache = cache or ManifestSourceCache()

    def register(self, source: ManifestSource) -> None:
        self.sources = [item for item in self.sources if item.name != source.name]
        self.sources.append(source)

    def resolve(
        self,
        request: ManifestRequest,
        capability: ManifestCapability = ManifestCapability.METADATA,
        preferred: Optional[Iterable[str]] = None,
    ) -> ManifestSourceResult:
        preferred_names = list(preferred or [])
        ordered = sorted(
            self.sources,
            key=lambda source: (
                preferred_names.index(source.name)
                if source.name in preferred_names
                else len(preferred_names)
            ),
        )
        failures = []
        for source in ordered:
            if not source.supports(capability) or not source.available(request):
                continue
            try:
                result = source.resolve(request)
                self.cache.record(result)
                return result
            except Exception as exc:
                failures.append(str(exc))
        detail = "; ".join(failures) if failures else "no compatible source is available"
        raise ManifestSourceError("registry", detail)


def create_default_registry(enrich_local: bool = True) -> ManifestSourceRegistry:
    from core.manifest_sources.hubcap import HubcapSource
    from core.manifest_sources.local_lua import LocalLuaSource

    return ManifestSourceRegistry([LocalLuaSource(enrich_from_steam=enrich_local), HubcapSource()])
