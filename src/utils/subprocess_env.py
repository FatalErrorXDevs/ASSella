"""Environment helpers for launching host executables from frozen builds."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping


def _bundle_roots(env: Mapping[str, str]) -> tuple[str, ...]:
    roots = []
    for value in (
        env.get("APPDIR"),
        getattr(sys, "_MEIPASS", None),
    ):
        if value:
            roots.append(os.path.realpath(value))
    return tuple(roots)


def _outside_bundle(path: str, roots: tuple[str, ...]) -> bool:
    if not path:
        return False

    resolved = os.path.realpath(path)
    for root in roots:
        try:
            if os.path.commonpath((resolved, root)) == root:
                return False
        except ValueError:
            continue
    return True


def get_external_process_env(
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return an environment safe for host binaries such as curl and dotnet.

    PyInstaller prepends its private library directory to ``LD_LIBRARY_PATH``
    so its executable can load the libraries bundled inside an AppImage.  A
    host binary inherits that override and can then load an incompatible
    bundled OpenSSL (or another library) alongside host libraries.  Restore
    the pre-PyInstaller path when it exists and remove any remaining paths
    inside the mounted application.
    """

    env = dict(os.environ if source is None else source)
    roots = _bundle_roots(env)

    original_library_path = env.pop("LD_LIBRARY_PATH_ORIG", None)
    library_path = (
        original_library_path
        if original_library_path is not None
        else env.get("LD_LIBRARY_PATH")
    )
    clean_paths = [
        path
        for path in (library_path or "").split(os.pathsep)
        if _outside_bundle(path, roots)
    ]
    if clean_paths:
        env["LD_LIBRARY_PATH"] = os.pathsep.join(clean_paths)
    else:
        env.pop("LD_LIBRARY_PATH", None)

    # Loader injection is unsafe for any executable outside the bundle.
    env.pop("LD_PRELOAD", None)
    env.pop("LD_AUDIT", None)
    return env
