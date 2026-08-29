import os
import unittest
from unittest.mock import patch

from utils.subprocess_env import get_external_process_env


class ExternalProcessEnvironmentTests(unittest.TestCase):
    def test_restores_original_library_path_and_removes_loader_injection(self):
        source = {
            "APPDIR": "/tmp/.mount_ASSella",
            "LD_LIBRARY_PATH": "/tmp/.mount_ASSella/usr/bin/_internal:/host/current",
            "LD_LIBRARY_PATH_ORIG": "/host/original",
            "LD_PRELOAD": "/tmp/.mount_ASSella/preload.so",
            "LD_AUDIT": "/tmp/.mount_ASSella/audit.so",
            "PATH": "/usr/bin",
        }

        env = get_external_process_env(source)

        self.assertEqual(env["LD_LIBRARY_PATH"], "/host/original")
        self.assertNotIn("LD_LIBRARY_PATH_ORIG", env)
        self.assertNotIn("LD_PRELOAD", env)
        self.assertNotIn("LD_AUDIT", env)

    def test_filters_bundle_paths_when_original_path_contains_appimage_paths(self):
        source = {
            "APPDIR": "/tmp/.mount_ASSella",
            "LD_LIBRARY_PATH": "/tmp/.mount_ASSella/usr/lib:/host/current",
            "LD_LIBRARY_PATH_ORIG": (
                "/tmp/.mount_ASSella/usr/lib:/opt/host/lib"
            ),
        }

        env = get_external_process_env(source)

        self.assertEqual(env["LD_LIBRARY_PATH"], "/opt/host/lib")

    def test_removes_library_path_when_only_bundle_paths_remain(self):
        source = {
            "APPDIR": "/tmp/.mount_ASSella",
            "LD_LIBRARY_PATH": "/tmp/.mount_ASSella/usr/bin/_internal",
        }

        with patch.object(os.path, "realpath", wraps=os.path.realpath):
            env = get_external_process_env(source)

        self.assertNotIn("LD_LIBRARY_PATH", env)


if __name__ == "__main__":
    unittest.main()
