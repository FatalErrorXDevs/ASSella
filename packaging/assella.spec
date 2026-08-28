from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent.parent
src = ROOT / "src"

hiddenimports = []
for package in ("core", "managers", "ui", "utils", "components"):
    hiddenimports.extend(collect_submodules(package))
hiddenimports.extend(["steam", "vdf", "urwid", "gevent", "gevent_eventemitter"])

datas = [
    (str(src / "res"), "res"),
    (str(src / "deps"), "deps"),
    (str(ROOT / "SLSsteam"), "SLSsteam"),
]

a = Analysis(
    [str(src / "main.py")],
    pathex=[str(src)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
