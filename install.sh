#!/usr/bin/env bash
# ASSella Installer Menu
# Usage: curl -fsSL https://raw.githubusercontent.com/niwia/ASSella/beta/install.sh | bash
set -eu

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Paths ──────────────────────────────────────────────────────────────────────
INSTALL_DIR="$HOME/.local/share/ACCELA"
DESKTOP_ENTRY="$HOME/.local/share/applications/accela.desktop"
ICON_PATH="$HOME/.local/share/icons/hicolor/256x256/apps/accela.png"
ASSELA_URL="https://github.com/niwia/ASSella/releases/latest/download/ASSella.AppImage"
ICON_URL="https://raw.githubusercontent.com/niwia/ASSella/beta/src/res/logo/icon.png"
HEADCRAB_DIR="$HOME/.headcrab"
HEADCRAB_DESKTOP="$HOME/.local/share/applications/headcrab.desktop"

# ── Helpers ────────────────────────────────────────────────────────────────────
print_header() {
    echo -e ""
    echo -e "${YELLOW}╔══════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║${NC}  ${BOLD}${CYAN}ASSella Installer Menu${NC}                  ${YELLOW}║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════╝${NC}"
    echo -e ""
}

is_headcrab_installed() {
    [ -d "$HEADCRAB_DIR" ] || [ -f "$HEADCRAB_DESKTOP" ]
}

refresh_desktop() {
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$(dirname "$DESKTOP_ENTRY")" 2>/dev/null || true
    fi
    if command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
    fi
}

# ── Actions ────────────────────────────────────────────────────────────────────

do_install_assela() {
    echo -e "${YELLOW}[INFO] Installing ASSella (pre-release / beta)...${NC}"
    mkdir -p "$INSTALL_DIR"

    # Back up original ACCELA if it's not a symlink and not already backed up
    if [ -f "$INSTALL_DIR/ACCELA.AppImage" ] && [ ! -L "$INSTALL_DIR/ACCELA.AppImage" ]; then
        echo -e "${YELLOW}[INFO] Backing up existing ACCELA.AppImage...${NC}"
        mv "$INSTALL_DIR/ACCELA.AppImage" "$INSTALL_DIR/ACCELA.AppImage.bak"
    fi

    echo -e "${YELLOW}[INFO] Downloading ASSella AppImage...${NC}"
    curl -L --progress-bar -o "$INSTALL_DIR/ASSella.AppImage" "$ASSELA_URL"
    chmod +x "$INSTALL_DIR/ASSella.AppImage"

    # Symlink so ACCELA.AppImage → ASSella.AppImage
    rm -f "$INSTALL_DIR/ACCELA.AppImage"
    ln -sf ASSella.AppImage "$INSTALL_DIR/ACCELA.AppImage"
    echo -e "${GREEN}[INFO] Created compatibility symlink ACCELA.AppImage → ASSella.AppImage${NC}"

    # Desktop entry
    if [ -f "$DESKTOP_ENTRY" ]; then
        sed -i 's/^Name=ACCELA$/Name=ASSella/' "$DESKTOP_ENTRY"
        echo -e "${GREEN}[INFO] Updated desktop shortcut to ASSella.${NC}"
    else
        mkdir -p "$(dirname "$DESKTOP_ENTRY")"
        cat >"$DESKTOP_ENTRY" <<EOL
[Desktop Entry]
Version=2.0
Name=ASSella
Comment=god is in the ass
Exec=$INSTALL_DIR/ACCELA.AppImage %u
Icon=accela
Terminal=false
Type=Application
Categories=Utility;Application;
MimeType=x-scheme-handler/accela;
EOL
        echo -e "${GREEN}[INFO] Created desktop shortcut.${NC}"
    fi

    # Icon
    echo -e "${YELLOW}[INFO] Applying application icon...${NC}"
    mkdir -p "$(dirname "$ICON_PATH")"
    curl -L --progress-bar -o "$ICON_PATH" "$ICON_URL"

    refresh_desktop

    echo -e ""
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ ASSella has been installed!           ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
    echo -e ""

    # Offer to run Headcrab if not already installed
    if ! is_headcrab_installed; then
        echo -e "${CYAN}[TIP] Headcrab is not detected on your system.${NC}"
        echo -e "      Headcrab installs the tools ASSella needs (SLSsteam, etc.)."
        echo -ne "      Would you like to run Headcrab now? [y/N] "
        read -r hc_answer </dev/tty
        case "$hc_answer" in
            y|Y|yes|Yes)
                do_run_headcrab
                ;;
            *)
                echo -e "${YELLOW}[INFO] Skipping Headcrab. You can install it later from ASSella → Settings → Tools.${NC}"
                ;;
        esac
    else
        echo -e "${GREEN}[INFO] Headcrab is already installed.${NC}"
    fi
}

do_uninstall_assela() {
    echo -e "${YELLOW}[INFO] Uninstalling ASSella...${NC}"
    local restored=false

    # Remove ASSella AppImage
    if [ -f "$INSTALL_DIR/ASSella.AppImage" ]; then
        rm -f "$INSTALL_DIR/ASSella.AppImage"
        echo -e "${GREEN}[INFO] Removed ASSella.AppImage${NC}"
    fi

    # Remove symlink
    if [ -L "$INSTALL_DIR/ACCELA.AppImage" ]; then
        rm -f "$INSTALL_DIR/ACCELA.AppImage"
        echo -e "${GREEN}[INFO] Removed ACCELA.AppImage symlink${NC}"
    fi

    # Restore original ACCELA if backup exists
    if [ -f "$INSTALL_DIR/ACCELA.AppImage.bak" ]; then
        echo -e "${YELLOW}[INFO] Found original ACCELA backup — restoring...${NC}"
        cp "$INSTALL_DIR/ACCELA.AppImage.bak" "$INSTALL_DIR/ACCELA.AppImage"
        chmod +x "$INSTALL_DIR/ACCELA.AppImage"
        restored=true
        echo -e "${GREEN}[INFO] Restored original ACCELA.AppImage${NC}"
    fi

    # Revert desktop entry
    if [ -f "$DESKTOP_ENTRY" ]; then
        sed -i 's/^Name=ASSella$/Name=ACCELA/' "$DESKTOP_ENTRY"
        echo -e "${GREEN}[INFO] Reverted desktop shortcut to ACCELA.${NC}"
    fi

    refresh_desktop

    echo -e ""
    if [ "$restored" = true ]; then
        echo -e "${GREEN}✓ ASSella uninstalled. Original ACCELA has been restored.${NC}"
    else
        echo -e "${GREEN}✓ ASSella uninstalled.${NC}"
        echo -e "${YELLOW}  No original ACCELA backup was found.${NC}"
    fi
    echo -e ""
}

do_run_headcrab() {
    if is_headcrab_installed; then
        echo -e "${CYAN}[INFO] Headcrab appears to already be installed.${NC}"
        echo -ne "       Run it again anyway? [y/N] "
        read -r confirm </dev/tty
        case "$confirm" in
            y|Y|yes|Yes) ;;
            *) echo -e "${YELLOW}[INFO] Cancelled.${NC}"; return ;;
        esac
    fi

    echo -e "${YELLOW}[INFO] Running Headcrab...${NC}"
    curl -fsSL headcrab.pages.dev | bash
    echo -e ""
    echo -e "${GREEN}✓ Headcrab finished.${NC}"
}

# ── Menu ────────────────────────────────────────────────────────────────────────

print_header

echo -e "  ${BOLD}1)${NC} Install / Update ASSella"
echo -e "  ${BOLD}2)${NC} Uninstall ASSella (+ restore ACCELA if backup exists)"
echo -e "  ${BOLD}3)${NC} Install / Run Headcrab"
echo -e "  ${BOLD}q)${NC} Quit"
echo -e ""
echo -ne "${CYAN}Choose an option [1/2/3/q]: ${NC}"

read -r choice </dev/tty

echo -e ""

case "$choice" in
    1)
        do_install_assela
        ;;
    2)
        echo -ne "${RED}Are you sure you want to uninstall ASSella? [y/N] ${NC}"
        read -r confirm </dev/tty
        case "$confirm" in
            y|Y|yes|Yes)
                do_uninstall_assela
                ;;
            *)
                echo -e "${YELLOW}[INFO] Cancelled.${NC}"
                ;;
        esac
        ;;
    3)
        do_run_headcrab
        ;;
    q|Q)
        echo -e "${YELLOW}Bye!${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}[ERROR] Invalid option: '$choice'${NC}"
        exit 1
        ;;
esac
