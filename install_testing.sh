#!/usr/bin/env bash
# ASSella Testing Installer (Extracted AppImage Edition)
set -euo pipefail

INSTALL_DIR="$HOME/.local/share/assella_testing"
DESKTOP_ENTRY="$HOME/.local/share/applications/assella_testing.desktop"
SYSTEMD_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SYSTEMD_DIR/assella-testing.service"
APPIMAGE_URL="https://github.com/niwia/ASSella/releases/download/v1.8h-alpha4/ASSella.AppImage"

echo "=== Installing ASSella Testing (Alpha) ==="
mkdir -p "$INSTALL_DIR"

echo "[INFO] Downloading ASSella AppImage..."
TEMP_APPIMAGE=$(mktemp)
curl -L --progress-bar -o "$TEMP_APPIMAGE" "$APPIMAGE_URL"
chmod +x "$TEMP_APPIMAGE"

echo "[INFO] Extracting AppImage..."
TEMP_DIR=$(mktemp -d)
mv "$TEMP_APPIMAGE" "$TEMP_DIR/ASSella.AppImage"
(cd "$TEMP_DIR" && ./ASSella.AppImage --appimage-extract >/dev/null)

echo "[INFO] Moving to $INSTALL_DIR..."
rm -rf "$INSTALL_DIR"
mv "$TEMP_DIR/squashfs-root" "$INSTALL_DIR"
rm -rf "$TEMP_DIR"

# Desktop Entry
echo "[INFO] Creating desktop entry..."
ICON_PATH="$INSTALL_DIR/usr/share/icons/hicolor/256x256/apps/accela.png"
if [ ! -f "$ICON_PATH" ]; then
    ICON_PATH="$INSTALL_DIR/bin/src/res/logo/icon.png"
fi

cat <<EOF > "$DESKTOP_ENTRY"
[Desktop Entry]
Name=ASSella Testing
Comment=ASSella Remote Control and Game Library (Testing Edition)
Exec="$INSTALL_DIR/AppRun"
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Game;Utility;
EOF
chmod +x "$DESKTOP_ENTRY"

if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

# Systemd User Service Setup
echo "[INFO] Setting up systemd user service..."
mkdir -p "$SYSTEMD_DIR"

# Stop existing service if running
systemctl --user stop assella-testing.service || true

cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=ASSella Testing Headless Server
After=network-online.target

[Service]
ExecStart=$INSTALL_DIR/AppRun --headless
Restart=on-failure
Environment=HOME=$HOME
Environment=XDG_RUNTIME_DIR=/run/user/1000

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload

echo ""
echo "=========================================================="
echo " ASSella Testing (v1.8h-alpha4) Installed Successfully!"
echo "=========================================================="
echo " 1. Desktop shortcut created: 'ASSella Testing' on your desktop/launcher"
echo " 2. Background service has been registered but is NOT started by default."
echo "    You can enable, configure, and start it from the new 'WebUI' tab"
echo "    in the ASSella Settings, or manually via systemctl:"
echo "      systemctl --user enable --now assella-testing"
echo "=========================================================="
