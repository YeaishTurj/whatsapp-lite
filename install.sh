#!/usr/bin/env bash
# WhatsApp Lite - Linux Installer
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

echo "==> Installing WhatsApp Lite..."

mkdir -p "$BIN_DIR" "$APP_DIR" "$ICON_DIR"

# Install script
chmod +x "$SCRIPT_DIR/src/whatsapp-lite.py"
ln -sf "$SCRIPT_DIR/src/whatsapp-lite.py" "$BIN_DIR/whatsapp-lite"

# Install icon
cp -f "$SCRIPT_DIR/assets/icon.svg" "$ICON_DIR/whatsapp.svg"

# Install desktop entry
sed "s|Exec=whatsapp-lite|Exec=$BIN_DIR/whatsapp-lite|g" \
    "$SCRIPT_DIR/assets/whatsapp-lite.desktop" > "$APP_DIR/whatsapp-lite.desktop"
chmod +x "$APP_DIR/whatsapp-lite.desktop"

# Update desktop database if available
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR"
fi

echo "==> Installation complete!"
echo "You can launch it by running: whatsapp-lite"
echo "Or search for 'WhatsApp' in your application menu."
