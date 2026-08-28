#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_NAME="${ASSELLA_APPIMAGE_NAME:-ASSella.AppImage}"
cd "$ROOT_DIR"

rm -rf build dist AppDir
python3 -m PyInstaller --noconfirm --clean packaging/assella.spec

mkdir -p AppDir/usr/bin AppDir/usr/share/icons/hicolor/256x256/apps
cp -a dist/ASSella/. AppDir/usr/bin/
ca_bundle="$(find AppDir/usr/bin -type f -path '*/certifi/cacert.pem' -print -quit)"
if [[ -z "$ca_bundle" || ! -s "$ca_bundle" ]]; then
  echo "Bundled certifi CA bundle was not found in the PyInstaller output" >&2
  exit 1
fi
# AppImage's runtime always starts AppRun. Keep this as a relative symlink so
# both the development and release images launch the PyInstaller executable.
ln -s usr/bin/ASSella AppDir/AppRun
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
ARCH=x86_64 "$TOOL" --no-appstream AppDir "$OUTPUT_NAME"
