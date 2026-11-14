#!/usr/bin/env bash
# WhatsApp Lite - Linux Uninstaller
set -e

echo "==> Uninstalling WhatsApp Lite..."

rm -f "$HOME/.local/bin/whatsapp-lite"
rm -f "$HOME/.local/share/applications/whatsapp-lite.desktop"
rm -f "$HOME/.local/share/pixmaps/whatsapp-lite.svg"
rm -f "$HOME/.local/share/pixmaps/whatsapp.svg"
rm -f "$HOME/.local/share/whatsapp-lite/icon.svg"

for theme in hicolor Papirus Papirus-Dark; do
    for size in scalable 16x16 22x22 24x24 32x32 48x48 64x64; do
        rm -f "$HOME/.local/share/icons/$theme/$size/apps/whatsapp-lite.svg"
        rm -f "$HOME/.local/share/icons/$theme/$size/apps/whatsapp.svg"
    done
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f "$HOME/.local/share/icons/$theme" 2>/dev/null || true
    fi
done

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications"
fi

echo "==> WhatsApp Lite uninstalled."
echo "Note: User profile data kept at ~/.local/share/whatsapp-lite"
