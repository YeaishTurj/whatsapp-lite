#!/usr/bin/env bash
# WhatsApp Lite - Linux Installer
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
DATA_DIR="$HOME/.local/share/whatsapp-lite"
PIXMAPS_DIR="$HOME/.local/share/pixmaps"

echo "==> Installing WhatsApp Lite..."

mkdir -p "$BIN_DIR" "$APP_DIR" "$DATA_DIR" "$PIXMAPS_DIR"

# Install script
chmod +x "$SCRIPT_DIR/src/whatsapp-lite.py"
ln -sf "$SCRIPT_DIR/src/whatsapp-lite.py" "$BIN_DIR/whatsapp-lite"
cp -f "$SCRIPT_DIR/src/whatsapp-lite.py" "$DATA_DIR/whatsapp-lite.py"

# Install official icon in dedicated app dir and pixmaps
cp -f "$SCRIPT_DIR/assets/icon.svg" "$DATA_DIR/icon.svg"
cp -f "$SCRIPT_DIR/assets/icon.svg" "$PIXMAPS_DIR/whatsapp-lite.svg"
cp -f "$SCRIPT_DIR/assets/icon.svg" "$PIXMAPS_DIR/whatsapp.svg"

# Install official icon across all common desktop icon themes
for theme in hicolor Papirus Papirus-Dark; do
    for size in scalable 16x16 22x22 24x24 32x32 48x48 64x64; do
        target_dir="$HOME/.local/share/icons/$theme/$size/apps"
        mkdir -p "$target_dir"
        cp -f "$SCRIPT_DIR/assets/icon.svg" "$target_dir/whatsapp-lite.svg"
        cp -f "$SCRIPT_DIR/assets/icon.svg" "$target_dir/whatsapp.svg"
    done
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f "$HOME/.local/share/icons/$theme" 2>/dev/null || true
    fi
done

# Install desktop entry
sed "s|Exec=whatsapp-lite|Exec=$BIN_DIR/whatsapp-lite|g" \
    "$SCRIPT_DIR/assets/whatsapp-lite.desktop" > "$APP_DIR/whatsapp-lite.desktop"
chmod +x "$APP_DIR/whatsapp-lite.desktop"

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR"
fi

echo "==> Installation complete!"
echo "Official WhatsApp logo installed across system themes and application launcher."
echo "You can launch it by running: whatsapp-lite"
