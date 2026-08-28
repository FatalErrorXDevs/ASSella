import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.manifest_sources.local_lua import LocalLuaSource
from core.manifest_sources.models import ManifestCapability, ManifestRequest
from core.manifest_sources.registry import ManifestSourceRegistry
from core.manifest_sources.base import ManifestSource
from core.manifest_sources.cache import ManifestSourceCache
try:
    from core import morrenus_api
except ModuleNotFoundError:
    # Dependency-free parser tests can still run in minimal environments.
    morrenus_api = None


class _Response:
    def __init__(self, payload=b"", status_code=200):
        self.content = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None


class _FailingSource(ManifestSource):
    name = "broken"
    capabilities = ManifestCapability.METADATA

    def resolve(self, request):
        raise RuntimeError("unavailable")


class ManifestSourceTests(unittest.TestCase):
    def test_local_lua_requires_manifest_gid_and_valid_depot_key(self):
        key = "a" * 64
        text = f'''addappid(12345, 0) -- Example Game
addappid(12346, 1, "{key}") -- Main depot
addappid(12347) -- DLC reference
setManifestid(12346, "987654321")
addtoken(12345, "token")
'''
        result = LocalLuaSource.parse_text(text)
        self.assertEqual(result.appid, "12345")
        self.assertEqual(set(result.depots), {"12346"})
        self.assertTrue(result.native_ready)
        self.assertEqual(result.manifest_gids, {"12346": "987654321"})

    def test_registry_falls_back_after_source_failure(self):
        class WorkingSource(ManifestSource):
            name = "working"
            capabilities = _FailingSource.capabilities

            def resolve(self, request):
                from core.manifest_sources.models import ManifestSourceResult

                return ManifestSourceResult(request.appid, self.name)

        with tempfile.TemporaryDirectory() as tmp:
            registry = ManifestSourceRegistry(
                [_FailingSource(), WorkingSource()],
                cache=ManifestSourceCache(Path(tmp)),
            )
            result = registry.resolve(ManifestRequest("123"))
            self.assertEqual(result.source, "working")

    @unittest.skipUnless(morrenus_api is not None, "HTTP dependencies are not installed")
    def test_empty_successful_response_is_retried(self):
        responses = [_Response(), _Response(), _Response(b"manifest")]
        with patch(
            "utils.isp_bypass.execute_hubcap_request",
            side_effect=responses,
        ) as request, patch("core.morrenus_api.time.sleep"):
            payload = morrenus_api._fetch_nonempty_response(
                "https://example.invalid/manifest", {}, "test manifest"
            )
        self.assertEqual(payload, b"manifest")
        self.assertEqual(request.call_count, 3)


if __name__ == "__main__":
    unittest.main()
