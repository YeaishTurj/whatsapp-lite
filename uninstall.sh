#!/usr/bin/env bash
# WhatsApp Lite - Linux Uninstaller
set -e

echo "==> Uninstalling WhatsApp Lite..."

rm -f "$HOME/.local/bin/whatsapp-lite"
rm -f "$HOME/.local/share/applications/whatsapp-lite.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/whatsapp.svg"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications"
fi

echo "==> WhatsApp Lite uninstalled."
echo "Note: User profile data kept at ~/.local/share/whatsapp-lite"
