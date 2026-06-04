#!/usr/bin/env bash
# ASSella Testing Installer & Manager (Alpha Branch)
# Usage: curl -fsSL https://raw.githubusercontent.com/niwia/ASSella/alpha/install_testing.sh | bash
set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Paths ──────────────────────────────────────────────────────────────────────
INSTALL_DIR="$HOME/.local/share/assella_testing"
DESKTOP_ENTRY="$HOME/.local/share/applications/assella_testing.desktop"
SYSTEMD_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SYSTEMD_DIR/assella-testing.service"
ZIP_URL="https://github.com/niwia/ASSella/archive/refs/heads/alpha.zip"
ICON_URL="https://raw.githubusercontent.com/niwia/ASSella/alpha/src/res/logo/icon.png"
ICON_PATH="$INSTALL_DIR/icon.png"

# ── Helpers ────────────────────────────────────────────────────────────────────
print_header() {
    echo -e ""
    echo -e "${YELLOW}╔══════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║${NC}  ${BOLD}${CYAN}ASSella Testing (Alpha) Manager${NC}        ${YELLOW}║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════╝${NC}"
    echo -e ""
}

refresh_desktop() {
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    fi
}

# ── Actions ────────────────────────────────────────────────────────────────────

do_install() {
    echo -e "${YELLOW}[INFO] Creating testing directory: $INSTALL_DIR...${NC}"
    mkdir -p "$INSTALL_DIR"

    echo -e "${YELLOW}[INFO] Downloading ASSella alpha source zip...${NC}"
    TEMP_ZIP=$(mktemp)
    curl -L --progress-bar -o "$TEMP_ZIP" "$ZIP_URL"

    echo -e "${YELLOW}[INFO] Extracting to $INSTALL_DIR...${NC}"
    # Extract to temp directory, then move contents to avoid nested folders
    TEMP_EXTRACT=$(mktemp -d)
    unzip -q "$TEMP_ZIP" -d "$TEMP_EXTRACT"
    
    # Sync extracted files to install dir
    rsync -a --delete "$TEMP_EXTRACT/ASSella-alpha/" "$INSTALL_DIR/"
    
    rm -f "$TEMP_ZIP"
    rm -rf "$TEMP_EXTRACT"

    # Download Icon
    echo -e "${YELLOW}[INFO] Downloading application icon...${NC}"
    curl -s -L -o "$ICON_PATH" "$ICON_URL" || true

    # Setup Virtual Environment
    VENV_DIR="$INSTALL_DIR/venv"
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}[INFO] Creating virtual environment...${NC}"
        python3 -m venv "$VENV_DIR"
    fi

    echo -e "${YELLOW}[INFO] Upgrading pip...${NC}"
    "$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip

    echo -e "${YELLOW}[INFO] Installing dependencies from requirements.txt...${NC}"
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        "$VENV_DIR/bin/python" -m pip install --quiet -r "$INSTALL_DIR/requirements.txt"
    else
        # Fallback if requirements.txt missing
        "$VENV_DIR/bin/python" -m pip install --quiet PyQt6 PyYAML requests zstandard steam just_playback cryptography protobuf vdf psutil configobj pillow urwid
    fi

    # Create Desktop Entry
    echo -e "${YELLOW}[INFO] Creating desktop entry...${NC}"
    cat <<EOF > "$DESKTOP_ENTRY"
[Desktop Entry]
Name=ASSella Testing
Comment=ASSella Remote Control and Game Library (Testing Edition)
Exec="$VENV_DIR/bin/python" "$INSTALL_DIR/src/main.py"
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Game;Utility;
EOF
    chmod +x "$DESKTOP_ENTRY"
    refresh_desktop

    echo -e "${GREEN}[SUCCESS] ASSella Testing installed successfully!${NC}"
    echo -e "${GREEN}Executable: $VENV_DIR/bin/python $INSTALL_DIR/src/main.py${NC}"
}

do_install_service() {
    if [ ! -d "$INSTALL_DIR" ] || [ ! -f "$INSTALL_DIR/src/main.py" ]; then
        echo -e "${RED}[ERROR] ASSella Testing must be installed first.${NC}"
        return 1
    fi

    echo -e "${YELLOW}[INFO] Creating systemd user service...${NC}"
    mkdir -p "$SYSTEMD_DIR"
    
    cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=ASSella Testing Headless Server
After=network-online.target

[Service]
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/src/main.py --headless --port 8765
Restart=on-failure
Environment=HOME=$HOME
Environment=XDG_RUNTIME_DIR=/run/user/1000

[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload
    systemctl --user enable assella-testing.service
    systemctl --user start assella-testing.service

    echo -e "${GREEN}[SUCCESS] Systemd user service installed and started!${NC}"
    echo -e "${GREEN}Web UI is running at http://steamdeck.local:8765${NC}"
    echo -e "${GREEN}You can check the service status with: systemctl --user status assella-testing${NC}"
}

do_stop_service() {
    echo -e "${YELLOW}[INFO] Stopping and disabling systemd user service...${NC}"
    systemctl --user stop assella-testing.service || true
    systemctl --user disable assella-testing.service || true
    rm -f "$SERVICE_FILE"
    systemctl --user daemon-reload
    echo -e "${GREEN}[SUCCESS] Service stopped and removed.${NC}"
}

do_uninstall() {
    echo -e "${YELLOW}[INFO] Uninstalling ASSella Testing...${NC}"
    do_stop_service || true
    rm -rf "$INSTALL_DIR"
    rm -f "$DESKTOP_ENTRY"
    refresh_desktop
    echo -e "${GREEN}[SUCCESS] ASSella Testing has been fully uninstalled.${NC}"
}

do_launch_gui() {
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}[INFO] Launching ASSella Testing GUI...${NC}"
        "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/src/main.py" &
    else
        echo -e "${RED}[ERROR] ASSella Testing is not installed.${NC}"
    fi
}

# ── Main Menu ─────────────────────────────────────────────────────────────────
main_menu() {
    while true; do
        print_header
        echo -e "  1) Install / Update ASSella Testing"
        
        # Check service status for indicator
        if systemctl --user is-active assella-testing &>/dev/null; then
            echo -e "  2) Restart / Reinstall Headless Service ${GREEN}(Running)${NC}"
            echo -e "  3) Stop / Remove Headless Service"
        else
            echo -e "  2) Install & Start Headless Service ${RED}(Stopped)${NC}"
            echo -e "  3) Remove Headless Service"
        fi
        
        echo -e "  4) Launch ASSella Testing GUI"
        echo -e "  5) Uninstall ASSella Testing"
        echo -e "  q) Quit"
        echo -e ""
        read -p "Select an option: " opt
        echo -e ""

        case $opt in
            1) do_install ;;
            2) do_install_service ;;
            3) do_stop_service ;;
            4) do_launch_gui ;;
            5)
                read -p "Are you sure you want to uninstall? (y/n): " confirm
                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    do_uninstall
                fi
                ;;
            q|Q) break ;;
            *) echo -e "${RED}Invalid option.${NC}" ;;
        esac
    done
}

# Non-interactive mode support
if [ $# -gt 0 ]; then
    case $1 in
        "install") do_install ;;
        "start-service") do_install_service ;;
        "stop-service") do_stop_service ;;
        "uninstall") do_uninstall ;;
        *) echo "Unknown command: $1" ;;
    esac
else
    main_menu
fi
