#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

rm -rf build dist AppDir
python3 -m PyInstaller --noconfirm --clean packaging/assella.spec

mkdir -p AppDir/usr/bin AppDir/usr/share/icons/hicolor/256x256/apps
cp -a dist/ASSella/. AppDir/usr/bin/
cp packaging/appimage.desktop AppDir/assella.desktop
cp src/res/logo/icon.png AppDir/usr/share/icons/hicolor/256x256/apps/assella.png
cp src/res/logo/icon.png AppDir/assella.png
chmod +x AppDir/usr/bin/ASSella

if [[ -x ./appimagetool ]]; then
  TOOL=./appimagetool
elif [[ -n "${RUNNER_TEMP:-}" && -x "$RUNNER_TEMP/appimagetool" ]]; then
  TOOL="$RUNNER_TEMP/appimagetool"
else
  echo "appimagetool not found" >&2
  exit 1
fi
ARCH=x86_64 "$TOOL" --no-appstream AppDir ASSella.AppImage
