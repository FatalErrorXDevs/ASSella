#!/usr/bin/env bash
set -eu

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DESTINATION="$HOME/.local/share/ACCELA"
DESKTOP_ENTRY="$HOME/.local/share/applications/accela.desktop"
ICON_PATH="$HOME/.local/share/icons/hicolor/256x256/apps/accela.png"

echo -e "${YELLOW}=========================================${NC}"
echo -e "${GREEN}        ASSella Installer & Patcher      ${NC}"
echo -e "${YELLOW}=========================================${NC}"

# 1. Ensure the installation directory exists
mkdir -p "$INSTALL_DESTINATION"

# 2. Check for old ACCELA.AppImage and back it up
if [ -f "$INSTALL_DESTINATION/ACCELA.AppImage" ] && [ ! -L "$INSTALL_DESTINATION/ACCELA.AppImage" ]; then
    echo -e "${YELLOW}[INFO] Backing up existing ACCELA.AppImage to ACCELA.AppImage.bak...${NC}"
    mv "$INSTALL_DESTINATION/ACCELA.AppImage" "$INSTALL_DESTINATION/ACCELA.AppImage.bak"
fi

# 3. Download the new ASSella.AppImage from GitHub Release
echo -e "${YELLOW}[INFO] Downloading ASSella beta AppImage...${NC}"
curl -L -o "$INSTALL_DESTINATION/ASSella.AppImage" \
  "https://github.com/niwia/ASSella/releases/download/v1.8d/ASSella.AppImage"

# 4. Make ASSella executable
chmod +x "$INSTALL_DESTINATION/ASSella.AppImage"

# 5. Create symlink so ACCELA.AppImage launches ASSella
ln -sf ASSella.AppImage "$INSTALL_DESTINATION/ACCELA.AppImage"
echo -e "${GREEN}[INFO] Created compatibility symlink.${NC}"

# 6. Update desktop entry display name to ASSella
if [ -f "$DESKTOP_ENTRY" ]; then
    echo -e "${YELLOW}[INFO] Updating application shortcut to show ASSella...${NC}"
    sed -i 's/^Name=ACCELA$/Name=ASSella/' "$DESKTOP_ENTRY"
else
    echo -e "${YELLOW}[INFO] Creating new desktop shortcut...${NC}"
    mkdir -p "$(dirname "$DESKTOP_ENTRY")"
    cat >"$DESKTOP_ENTRY" <<EOL
[Desktop Entry]
Version=2.0
Name=ASSella
Comment=god is in the ass
Exec=$INSTALL_DESTINATION/ACCELA.AppImage %u
Icon=accela
Terminal=false
Type=Application
Categories=Utility;Application;
MimeType=x-scheme-handler/accela;
EOL
fi

# 7. Download and apply the new orange/navy logo icon
echo -e "${YELLOW}[INFO] Applying new orange/navy application icon...${NC}"
mkdir -p "$(dirname "$ICON_PATH")"
curl -L -o "$ICON_PATH" \
  "https://raw.githubusercontent.com/niwia/ASSella/beta/src/res/logo/icon.png"

# Update icon cache and desktop database
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$(dirname "$DESKTOP_ENTRY")" 2>/dev/null
fi
if [ -z "${XDG_CURRENT_DESKTOP:-}" ] || [[ "$XDG_CURRENT_DESKTOP" != *"KDE"* ]]; then
    command -v gtk-update-icon-cache &>/dev/null && gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}✓ ASSella has been installed & patched!  ${NC}"
echo -e "${GREEN}=========================================${NC}"
