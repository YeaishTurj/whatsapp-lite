# WhatsApp Lite (Linux)

A lightweight, privacy-focused WhatsApp desktop client for Linux built on **PyQt6** and **QtWebEngine**.

Designed as a high-performance alternative to bloated Electron wrappers, consuming ~75% less RAM while maintaining full feature parity with WhatsApp Web (including WebRTC voice/video calls, notifications, and system tray integration).

---

## Highlights

- **Lightweight Memory Footprint**: Starts at **~180 MB – 250 MB RAM** (vs 800 MB – 1.2 GB+ in Electron wrappers).
- **Audio & Video Calls**: Full WebRTC calling support with auto-granted media permissions (camera, microphone, screen sharing).
- **System Tray Integration**:
  - Wayland / Hyprland native StatusNotifierItem tray support.
  - Dynamic unread message counter badge rendered directly onto the tray icon.
  - Quick actions: Show/Hide, Mute Audio, Reload, and Quit.
- **Minimize to Tray**: Closing the window hides it to the tray to keep receiving calls and notifications without cluttering your workspace.
- **Single-Instance Enforcement**: Launching WhatsApp again from an app menu focuses the existing running window.
- **Persistent Session**: Keeps your login session safe across reboots under `~/.local/share/whatsapp-lite`.
- **Keyboard Shortcuts**:
  - `Ctrl + Q` : Quit application completely
  - `Ctrl + W` / `Esc` : Hide to system tray
  - `Ctrl + R` / `F5` : Reload page
  - `Ctrl + +` / `Ctrl + -` / `Ctrl + 0` : Zoom in / out / reset zoom

---

## Dependencies

### Arch Linux / Manjaro
```bash
sudo pacman -S python-pyqt6 python-pyqt6-webengine qt6-wayland
```

### Fedora
```bash
sudo dnf install python3-pyqt6 python3-pyqt6-webengine qt6-qtwayland
```

### Ubuntu / Debian
```bash
sudo apt install python3-pyqt6 python3-pyqt6.qtwebengine qt6-wayland
```

---

## Installation

Clone the repository and run the install script:

```bash
git clone https://github.com/YeaishTurj/whatsapp-lite.git
cd whatsapp-lite
chmod +x install.sh
./install.sh
```

Now launch it from your app launcher (Rofi, Wofi, Walker, GNOME, etc.) by searching for **WhatsApp**, or run:

```bash
whatsapp-lite
```

To uninstall:
```bash
./uninstall.sh
```

---

## Window Rules (Hyprland / Sway)

For tiling window managers like **Hyprland**, add this to your `~/.config/hypr/hyprland.conf`:

```ini
windowrulev2 = float, class:^(whatsapp-lite)$
windowrulev2 = size 1120 780, class:^(whatsapp-lite)$
windowrulev2 = center, class:^(whatsapp-lite)$
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
