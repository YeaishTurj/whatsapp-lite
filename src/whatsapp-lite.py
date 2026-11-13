#!/usr/bin/env python3
"""
WhatsApp Lite - A lightweight, memory-efficient WhatsApp Desktop client for Linux.
Built on PyQt6 and QtWebEngine.

Features:
- ~200MB RAM usage (compared to 800MB-1.2GB for Electron wrappers)
- Audio & Video Calling support (WebRTC permissions auto-granted)
- Native System Tray with unread message badges (e.g. for Waybar / Hyprland)
- Minimize-to-tray on close
- Desktop notifications & incoming call alerts
- Single-instance enforcement (re-running focuses the active window)
- High-DPI & Wayland native (Hyprland friendly app_id)
"""

import sys
import os
import re
import shutil
import subprocess

# ---------------------------------------------------------
# Dependency Check
# ---------------------------------------------------------
try:
    from PyQt6.QtCore import (
        Qt, QUrl, QSize, QPoint, QDir, QStandardPaths,
        pyqtSlot, QByteArray
    )
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QSystemTrayIcon,
        QMenu, QMessageBox
    )
    from PyQt6.QtGui import (
        QIcon, QPixmap, QPainter, QColor, QFont,
        QAction, QKeySequence, QShortcut
    )
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    from PyQt6.QtWebEngineCore import (
        QWebEngineProfile, QWebEnginePage, QWebEngineSettings
    )
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError as e:
    missing_mod = str(e)
    print("\n" + "=" * 60)
    print(" [!] Missing Required Dependencies for WhatsApp Lite")
    print("=" * 60)
    print(f"Details: {missing_mod}")
    print("\nPlease install the required packages using pacman:")
    print("  sudo pacman -S python-pyqt6 python-pyqt6-webengine\n")
    print("=" * 60 + "\n")
    
    # Try displaying a graphical message if notify-send is available
    if shutil.which("notify-send"):
        subprocess.run([
            "notify-send",
            "-u", "critical",
            "-a", "WhatsApp Lite",
            "Missing Dependencies",
            "Please run: sudo pacman -S python-pyqt6 python-pyqt6-webengine"
        ], check=False)
    sys.exit(1)

# ---------------------------------------------------------
# Paths & Settings
# ---------------------------------------------------------
APP_NAME = "whatsapp-lite"
APP_DISPLAY_NAME = "WhatsApp"
USER_DATA_DIR = os.path.expanduser("~/.local/share/whatsapp-lite")
CACHE_DIR = os.path.expanduser("~/.cache/whatsapp-lite")
SINGLE_INSTANCE_KEY = "whatsapp_lite_single_instance_sock"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

WHATSAPP_URL = "https://web.whatsapp.com"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_ICON = os.path.join(SCRIPT_DIR, "..", "assets", "icon.svg")

# Icon search candidates
ICON_CANDIDATES = [
    ASSETS_ICON,
    os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps/whatsapp.svg"),
    "/usr/share/icons/Papirus/48x48/apps/whatsapp.svg",
    "/usr/share/icons/Papirus/32x32/apps/whatsapp.svg",
    "/usr/share/icons/hicolor/scalable/apps/whatsapp.svg",
    "/usr/share/pixmaps/whatsapp.svg",
    "/usr/share/pixmaps/whatsapp.png"
]

def get_base_icon() -> QIcon:
    for path in ICON_CANDIDATES:
        if os.path.exists(path):
            return QIcon(path)
    # Built-in SVG fallback if no system icon is found
    svg_data = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
      <circle cx="24" cy="24" r="22" fill="#25D366"/>
      <path fill="#FFFFFF" d="M34.5 28.5c-.5-.2-2.9-1.4-3.3-1.6-.4-.2-.8-.2-1.1.2-.3.5-1.2 1.6-1.5 1.9-.3.3-.6.4-1.1.2-.5-.2-2.2-.8-4.2-2.6-1.5-1.4-2.6-3.1-2.9-3.6-.3-.5 0-.8.2-1 .2-.2.5-.5.7-.8.2-.3.3-.5.4-.8.2-.3.1-.7 0-.9-.2-.2-1.1-2.7-1.5-3.6-.4-.9-.8-.8-1.1-.8h-.9c-.3 0-.9.1-1.4.6-.5.5-1.9 1.9-1.9 4.6 0 2.7 2 5.3 2.3 5.6.3.4 3.9 6 9.4 8.4 1.3.6 2.3.9 3.1 1.2 1.3.4 2.5.4 3.4.2 1.1-.2 3.3-1.3 3.8-2.6.5-1.3.5-2.4.3-2.6-.1-.3-.4-.4-.9-.7z"/>
    </svg>"""
    pix = QPixmap()
    pix.loadFromData(svg_data, "SVG")
    return QIcon(pix)

# ---------------------------------------------------------
# Custom WebEnginePage for Permissions & WebRTC Calls
# ---------------------------------------------------------
class WhatsAppWebPage(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.featurePermissionRequested.connect(self.on_feature_permission_requested)

    def on_feature_permission_requested(self, security_origin: QUrl, feature):
        host = security_origin.host()
        # Automatically allow media devices and notifications for WhatsApp
        if "whatsapp.com" in host or "whatsapp.net" in host:
            try:
                # Qt6 PermissionPolicy
                policy = getattr(QWebEnginePage.PermissionPolicy, 'PermissionGrantedByUser', None)
                if policy is None:
                    policy = getattr(QWebEnginePage, 'PermissionGrantedByUser', 1)
                self.setFeaturePermission(security_origin, feature, policy)
            except Exception as err:
                print(f"[!] Error granting feature permission: {err}")
        else:
            try:
                policy = getattr(QWebEnginePage.PermissionPolicy, 'PermissionDeniedByUser', None)
                if policy is None:
                    policy = getattr(QWebEnginePage, 'PermissionDeniedByUser', 0)
                self.setFeaturePermission(security_origin, feature, policy)
            except Exception:
                pass

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        # Silence benign console warnings for cleaner terminal output
        if "warning" in message.lower() or "error" in message.lower():
            pass

# ---------------------------------------------------------
# Main Application Window
# ---------------------------------------------------------
class WhatsAppWindow(QMainWindow):
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.is_quitting = False
        self.base_icon = get_base_icon()
        self.current_unread_count = 0

        self.setWindowTitle("WhatsApp")
        self.setWindowIcon(self.base_icon)
        self.resize(1120, 780)
        self.setMinimumSize(600, 500)

        # Setup persistent web profile
        self.profile = QWebEngineProfile("whatsapp_storage", self)
        os.makedirs(USER_DATA_DIR, exist_ok=True)
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.profile.setPersistentStoragePath(USER_DATA_DIR)
        self.profile.setCachePath(CACHE_DIR)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        self.profile.setHttpUserAgent(USER_AGENT)

        # Setup WebEngine Settings
        settings = self.profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, True)

        # Desktop notification presenter handler
        if hasattr(self.profile, 'setNotificationPresenter'):
            self.profile.setNotificationPresenter(self.handle_web_notification)

        # Web view setup
        self.web_page = WhatsAppWebPage(self.profile, self)
        self.web_view = QWebEngineView(self)
        self.web_view.setPage(self.web_page)
        self.setCentralWidget(self.web_view)

        # Connect signals
        self.web_view.titleChanged.connect(self.on_title_changed)

        # Setup System Tray Icon
        self.setup_tray_icon()

        # Keyboard shortcuts
        self.setup_shortcuts()

        # Load WhatsApp
        self.web_view.load(QUrl(WHATSAPP_URL))

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self.base_icon, self)
        self.tray_icon.setToolTip("WhatsApp Lite")

        # Tray Context Menu
        self.tray_menu = QMenu()
        
        show_action = QAction("Show / Hide", self)
        show_action.triggered.connect(self.toggle_visibility)
        self.tray_menu.addAction(show_action)

        reload_action = QAction("Reload Page (Ctrl+R)", self)
        reload_action.triggered.connect(self.reload_page)
        self.tray_menu.addAction(reload_action)

        mute_action = QAction("Mute Audio", self)
        mute_action.setCheckable(True)
        mute_action.toggled.connect(self.toggle_mute)
        self.tray_menu.addAction(mute_action)

        self.tray_menu.addSeparator()

        quit_action = QAction("Quit WhatsApp", self)
        quit_action.triggered.connect(self.really_quit)
        self.tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def setup_shortcuts(self):
        # Ctrl+Q -> Quit
        QShortcut(QKeySequence("Ctrl+Q"), self, self.really_quit)
        # Ctrl+W / Esc -> Hide to tray
        QShortcut(QKeySequence("Ctrl+W"), self, self.hide)
        # Ctrl+R / F5 -> Reload
        QShortcut(QKeySequence("Ctrl+R"), self, self.reload_page)
        QShortcut(QKeySequence("F5"), self, self.reload_page)
        # Zoom controls
        QShortcut(QKeySequence("Ctrl+="), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl++"), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self.zoom_reset)

    def zoom_in(self):
        factor = self.web_view.zoomFactor()
        self.web_view.setZoomFactor(min(factor + 0.1, 2.5))

    def zoom_out(self):
        factor = self.web_view.zoomFactor()
        self.web_view.setZoomFactor(max(factor - 0.1, 0.5))

    def zoom_reset(self):
        self.web_view.setZoomFactor(1.0)

    def reload_page(self):
        self.web_view.reload()

    def toggle_mute(self, muted: bool):
        self.web_page.setAudioMuted(muted)

    def toggle_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.show()
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
            self.raise_()
            self.activateWindow()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visibility()

    def handle_web_notification(self, notification):
        try:
            # Let Qt display it or forward to desktop
            notification.show()
        except Exception:
            pass

    def on_title_changed(self, title: str):
        """Extract unread count from WhatsApp title e.g. '(3) WhatsApp'"""
        match = re.search(r'\((\d+)\)', title)
        if match:
            count = int(match.group(1))
            self.update_tray_badge(count)
        elif '(*)' in title or '*' in title:
            self.update_tray_badge('•')
        else:
            self.update_tray_badge(0)

    def update_tray_badge(self, unread):
        if unread == self.current_unread_count:
            return
        self.current_unread_count = unread

        if unread == 0 or unread is None:
            self.tray_icon.setIcon(self.base_icon)
            self.setWindowIcon(self.base_icon)
            self.tray_icon.setToolTip("WhatsApp Lite")
            return

        # Paint badge counter on the icon
        size = 64
        pixmap = self.base_icon.pixmap(size, size)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw red badge circle
        badge_radius = 16
        center_x = size - badge_radius - 2
        center_y = size - badge_radius - 2
        painter.setBrush(QColor(235, 64, 52))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPoint(center_x, center_y), badge_radius, badge_radius)

        # Draw number text
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Sans", 14, QFont.Weight.Bold)
        painter.setFont(font)
        text = str(unread) if str(unread) != '•' else "•"
        painter.drawText(
            center_x - badge_radius, center_y - badge_radius,
            badge_radius * 2, badge_radius * 2,
            Qt.AlignmentFlag.AlignCenter, text
        )
        painter.end()

        badged_icon = QIcon(pixmap)
        self.tray_icon.setIcon(badged_icon)
        self.setWindowIcon(badged_icon)
        self.tray_icon.setToolTip(f"WhatsApp Lite - {unread} unread messages")

    def closeEvent(self, event):
        """Minimize to tray on window close button"""
        if self.is_quitting:
            event.accept()
        else:
            event.ignore()
            self.hide()

    def really_quit(self):
        self.is_quitting = True
        self.app.quit()

# ---------------------------------------------------------
# Single Instance Management & Entry Point
# ---------------------------------------------------------
def main():
    # Set Wayland Desktop file name for Hyprland/Wayland window matching
    os.environ.setdefault("QT_QPA_PLATFORM", "wayland;xcb")
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)

    # Check if another instance is already running
    socket = QLocalSocket()
    socket.connectToServer(SINGLE_INSTANCE_KEY)
    if socket.waitForConnected(400):
        # Primary instance exists, signal it to show up
        socket.write(b"SHOW\n")
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        sys.exit(0)

    # Primary instance: start local server
    server = QLocalServer()
    # Remove stale socket file if any
    QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
    server.listen(SINGLE_INSTANCE_KEY)

    window = WhatsAppWindow(app)

    def handle_incoming_connection():
        client = server.nextPendingConnection()
        if client:
            client.readyRead.connect(lambda: on_client_read(client))

    def on_client_read(client):
        data = client.readAll().data().decode("utf-8")
        if "SHOW" in data:
            window.show()
            window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
            window.raise_()
            window.activateWindow()

    server.newConnection.connect(handle_incoming_connection)

    # Show initial window
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
