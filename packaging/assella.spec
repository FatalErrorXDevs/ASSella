from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ``SPECPATH`` is the directory containing this spec (``packaging``), so its
# parent is the repository root.
ROOT = Path(SPECPATH).parent
src = ROOT / "src"

hiddenimports = []
for package in ("core", "managers", "ui", "utils", "components"):
    hiddenimports.extend(collect_submodules(package))
hiddenimports.extend(collect_submodules("urwid"))
hiddenimports.extend(["steam", "vdf", "urwid", "gevent", "gevent_eventemitter"])
hiddenimports.append("certifi")

datas = [
    (str(src / "res"), "res"),
    (str(src / "deps"), "deps"),
    (str(ROOT / "SLSsteam"), "SLSsteam"),
]
datas.extend(collect_data_files("certifi"))

a = Analysis(
    [str(src / "main.py")],
    pathex=[str(src)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "packaging" / "runtime_ssl.py")],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    name="ASSella",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    exclude_binaries=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="ASSella",
)
