from __future__ import annotations

from abc import ABC, abstractmethod

from core.manifest_sources.models import (
    ManifestCapability,
    ManifestRequest,
    ManifestSourceResult,
)


class ManifestSourceError(RuntimeError):
    def __init__(self, source: str, message: str) -> None:
        self.source = source
        super().__init__(f"{source}: {message}")


class ManifestSource(ABC):
    name: str
    capabilities: ManifestCapability

    def supports(self, capability: ManifestCapability) -> bool:
        return (self.capabilities & capability) == capability

    def available(self, request: ManifestRequest) -> bool:
        return True

    @abstractmethod
    def resolve(self, request: ManifestRequest) -> ManifestSourceResult:
        raise NotImplementedError
