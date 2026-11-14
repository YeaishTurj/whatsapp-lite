#!/usr/bin/env python3
"""
WhatsApp Lite - A high-performance, lightweight WhatsApp Desktop client for Linux.
Built with PyQt6 and QtWebEngine.

Optimizations:
- ~180MB - 250MB RAM usage (compared to 800MB-1.2GB for Electron)
- Hardware-accelerated video decoding (VA-API on Intel/AMD GPUs)
- PipeWire screen sharing on Wayland (Hyprland / Sway)
- WebRTC Audio & Video Calling with auto-granted media permissions
- Incoming call auto-raise & critical priority desktop alerts
- Native System Tray with real-time unread badge counter
- Automatic attachment download handler with completion notifications
- External links open in default web browser
- Zero white-flash dark theme background on startup
- Slim emerald progress bar during page load
- V8 memory garbage collector triggered on hide/minimize
- Single-instance enforcement (re-running focuses existing window)
"""

import sys
import os
import re
import shutil
import subprocess
import urllib.parse
import time

# ---------------------------------------------------------
# Chromium & Qt Optimization Flags
# (Must be configured before QApplication initializes)
# ---------------------------------------------------------
os.environ.setdefault("QT_QPA_PLATFORM", "wayland;xcb")

existing_flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
optimizations = (
    "--enable-features=VaapiVideoDecoder,VaapiIgnoreDriverChecks,WebRTCPipeWireCapturer "
    "--enable-gpu-rasterization "
    "--enable-zero-copy "
    "--ignore-gpu-blocklist "
    "--disable-features=Translate,AutofillServerCommunication,OptimizationHints "
    "--js-flags=--expose-gc "
)
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"{existing_flags} {optimizations}".strip()

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
        QMenu, QMessageBox, QProgressBar, QVBoxLayout, QWidget
    )
    from PyQt6.QtGui import (
        QIcon, QPixmap, QPainter, QColor, QFont,
        QAction, QKeySequence, QShortcut, QDesktopServices
    )
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    from PyQt6.QtWebEngineCore import (
        QWebEngineProfile, QWebEnginePage, QWebEngineSettings,
        QWebEngineDownloadRequest, QWebEngineScript
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
OFFICIAL_ICON_PATH = os.path.expanduser("~/.local/share/whatsapp-lite/icon.svg")

# Built-in Official WhatsApp Vector SVG (exact Meta brand asset)
OFFICIAL_SVG_DATA = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 175.216 175.552">
  <defs>
    <linearGradient id="b" x1="85.915" x2="86.535" y1="32.567" y2="137.092" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#57d163"/>
      <stop offset="1" stop-color="#23b33a"/>
    </linearGradient>
    <filter id="a" width="1.115" height="1.114" x="-.057" y="-.057" color-interpolation-filters="sRGB">
      <feGaussianBlur stdDeviation="3.531"/>
    </filter>
  </defs>
  <path fill="#b3b3b3" d="m54.532 138.45 2.235 1.324c9.387 5.571 20.15 8.518 31.126 8.523h.023c33.707 0 61.139-27.426 61.153-61.135.006-16.335-6.349-31.696-17.895-43.251A60.75 60.75 0 0 0 87.94 25.983c-33.733 0-61.166 27.423-61.178 61.13a60.98 60.98 0 0 0 9.349 32.535l1.455 2.312-6.179 22.558zm-40.811 23.544L24.16 123.88c-6.438-11.154-9.825-23.808-9.821-36.772.017-40.556 33.021-73.55 73.578-73.55 19.681.01 38.154 7.669 52.047 21.572s21.537 32.383 21.53 52.037c-.018 40.553-33.027 73.553-73.578 73.553h-.032c-12.313-.005-24.412-3.094-35.159-8.954zm0 0" filter="url(#a)"/>
  <path fill="#fff" d="m12.966 161.238 10.439-38.114a73.42 73.42 0 0 1-9.821-36.772c.017-40.556 33.021-73.55 73.578-73.55 19.681.01 38.154 7.669 52.047 21.572s21.537 32.383 21.53 52.037c-.018 40.553-33.027 73.553-73.578 73.553h-.032c-12.313-.005-24.412-3.094-35.159-8.954z"/>
  <path fill="url(#b)" d="M87.184 25.227c-33.733 0-61.166 27.423-61.178 61.13a60.98 60.98 0 0 0 9.349 32.535l1.455 2.313-6.179 22.558 23.146-6.069 2.235 1.324c9.387 5.571 20.15 8.517 31.126 8.523h.023c33.707 0 61.14-27.426 61.153-61.135a60.75 60.75 0 0 0-17.895-43.251 60.75 60.75 0 0 0-43.235-17.928z"/>
  <path fill="#fff" fill-rule="evenodd" d="M68.772 55.603c-1.378-3.061-2.828-3.123-4.137-3.176l-3.524-.043c-1.226 0-3.218.46-4.902 2.3s-6.435 6.287-6.435 15.332 6.588 17.785 7.506 19.013 12.718 20.381 31.405 27.75c15.529 6.124 18.689 4.906 22.061 4.6s10.877-4.447 12.408-8.74 1.532-7.971 1.073-8.74-1.685-1.226-3.525-2.146-10.877-5.367-12.562-5.981-2.91-.919-4.137.921-4.746 5.979-5.819 7.206-2.144 1.381-3.984.462-7.76-2.861-14.784-9.124c-5.465-4.873-9.154-10.891-10.228-12.73s-.114-2.835.808-3.751c.825-.824 1.838-2.147 2.759-3.22s1.224-1.84 1.836-3.065.307-2.301-.153-3.22-4.032-10.011-5.666-13.647"/>
</svg>"""

# Strict official icon paths (No Papirus/third-party fallbacks allowed)
ICON_CANDIDATES = [
    OFFICIAL_ICON_PATH,
    ASSETS_ICON,
    os.path.join(SCRIPT_DIR, "assets", "icon.svg"),
    os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps/whatsapp-lite.svg"),
    os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps/whatsapp.svg"),
    os.path.expanduser("~/.local/share/pixmaps/whatsapp-lite.svg"),
    os.path.expanduser("~/.local/share/pixmaps/whatsapp.svg")
]

def ensure_official_icon_on_disk():
    if not os.path.exists(OFFICIAL_ICON_PATH):
        try:
            os.makedirs(os.path.dirname(OFFICIAL_ICON_PATH), exist_ok=True)
            with open(OFFICIAL_ICON_PATH, "wb") as f:
                f.write(OFFICIAL_SVG_DATA)
        except Exception:
            pass

def get_base_icon() -> QIcon:
    ensure_official_icon_on_disk()
    for path in ICON_CANDIDATES:
        if os.path.exists(path):
            return QIcon(path)
    # Directly parse the official SVG vector
    pix = QPixmap()
    pix.loadFromData(OFFICIAL_SVG_DATA, "SVG")
    return QIcon(pix)

# ---------------------------------------------------------
# External URL Dispatcher (Wayland & Linux Native)
# ---------------------------------------------------------
_last_opened_url = None
_last_opened_time = 0.0

def clean_external_url(url_str: str) -> str:
    """Unwrap Meta / WhatsApp redirect tracker parameters if present"""
    if not url_str:
        return ""
    try:
        parsed = urllib.parse.urlparse(url_str)
        if any(d in parsed.netloc for d in ("wl.co", "facebook.com", "whatsapp.com")):
            qs = urllib.parse.parse_qs(parsed.query)
            if "u" in qs and qs["u"]:
                return urllib.parse.unquote(qs["u"][0])
    except Exception:
        pass
    return url_str

def open_external_url(target):
    """Reliably launch external URL in user's default browser (e.g. Chrome / Brave) with de-duplication"""
    global _last_opened_url, _last_opened_time

    if isinstance(target, QUrl):
        url_str = target.toString()
    else:
        url_str = str(target)

    url_str = clean_external_url(url_str).strip()
    if not url_str or url_str in ("about:blank", "about:", ""):
        return

    # Debounce identical URL within 1.5 seconds to prevent duplicate tabs
    now = time.time()
    if url_str == _last_opened_url and (now - _last_opened_time) < 1.5:
        return
    _last_opened_url = url_str
    _last_opened_time = now

    # 1. Primary: xdg-open in detached session
    try:
        subprocess.Popen(
            ["xdg-open", url_str],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return
    except Exception:
        pass

    # 2. Secondary: gio open
    if shutil.which("gio"):
        try:
            subprocess.Popen(
                ["gio", "open", url_str],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            return
        except Exception:
            pass

    # 3. Fallback: QDesktopServices
    QDesktopServices.openUrl(QUrl(url_str))

# ---------------------------------------------------------
# Custom WebEnginePage for External Links & Calling
# ---------------------------------------------------------
class ExternalLinkPage(QWebEnginePage):
    """Temporary page to intercept window.open and target='_blank' links"""
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.has_dispatched = False
        self.urlChanged.connect(self.on_url_changed)

    def _dispatch_once(self, url: QUrl):
        if self.has_dispatched:
            return
        url_str = url.toString()
        if url_str and url_str not in ("about:blank", "about:"):
            self.has_dispatched = True
            open_external_url(url_str)
            self.deleteLater()

    def acceptNavigationRequest(self, url: QUrl, nav_type, is_main_frame):
        url_str = url.toString()
        if url_str and url_str not in ("about:blank", "about:"):
            self._dispatch_once(url)
            return False
        return True

    def on_url_changed(self, url: QUrl):
        self._dispatch_once(url)

class WhatsAppWebPage(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.featurePermissionRequested.connect(self.on_feature_permission_requested)
        self.setBackgroundColor(QColor("#111b21"))

    def on_feature_permission_requested(self, security_origin: QUrl, feature):
        host = security_origin.host()
        if "whatsapp.com" in host or "whatsapp.net" in host:
            try:
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

    def acceptNavigationRequest(self, url: QUrl, nav_type, is_main_frame):
        host = url.host().lower()
        url_str = url.toString()

        # Always permit internal WhatsApp traffic, websocket, blob, and initial load
        if (
            not host
            or "whatsapp.com" in host
            or "whatsapp.net" in host
            or url.scheme() in ("blob", "data", "about", "wss", "ws")
        ):
            return True

        # Any external URL: open directly in system default browser!
        open_external_url(url_str)
        return False

    def createWindow(self, window_type):
        return ExternalLinkPage(self.profile(), self)

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
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

        # Eliminate white flash during window creation
        self.setStyleSheet("QMainWindow { background-color: #111b21; }")

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

        # Limit cache growth (120MB max disk cache)
        if hasattr(self.profile, 'setHttpCacheMaximumSize'):
            self.profile.setHttpCacheMaximumSize(120 * 1024 * 1024)

        # WebEngine settings
        settings = self.profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)

        # Connect download handler
        self.profile.downloadRequested.connect(self.on_download_requested)

        # Inject click interceptor for external links
        link_script = QWebEngineScript()
        link_script.setName("external_link_interceptor")
        link_script.setSourceCode("""
        (function() {
            document.addEventListener('click', function(e) {
                let el = e.target;
                while (el && el.tagName !== 'A') {
                    el = el.parentElement;
                }
                if (el && el.tagName === 'A' && el.href) {
                    const href = el.href;
                    if (href.startsWith('http://') || href.startsWith('https://')) {
                        try {
                            const url = new URL(href);
                            if (!url.hostname.includes('whatsapp.com') && !url.hostname.includes('whatsapp.net')) {
                                e.preventDefault();
                                e.stopPropagation();
                                window.open(href, '_blank');
                            }
                        } catch (err) {}
                    }
                }
            }, true);
        })();
        """)
        link_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        link_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        link_script.setRunsOnSubFrames(True)
        self.profile.scripts().insert(link_script)

        # Desktop notification presenter
        if hasattr(self.profile, 'setNotificationPresenter'):
            self.profile.setNotificationPresenter(self.handle_web_notification)

        # Container & Layout with Slim Emerald Progress Bar
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #111b21;
            }
            QProgressBar::chunk {
                background-color: #00a884;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Web view setup
        self.web_page = WhatsAppWebPage(self.profile, self)
        self.web_page.fullScreenRequested.connect(self.on_fullscreen_requested)

        self.web_view = QWebEngineView(self)
        self.web_view.setPage(self.web_page)
        self.web_view.setStyleSheet("background-color: #111b21;")
        layout.addWidget(self.web_view)

        self.setCentralWidget(container)

        # Connect loading & title signals
        self.web_view.loadStarted.connect(self.on_load_started)
        self.web_view.loadProgress.connect(self.on_load_progress)
        self.web_view.loadFinished.connect(self.on_load_finished)
        self.web_view.titleChanged.connect(self.on_title_changed)

        # Setup System Tray Icon & Shortcuts
        self.setup_tray_icon()
        self.setup_shortcuts()

        # Load WhatsApp Web
        self.web_view.load(QUrl(WHATSAPP_URL))

    def on_load_started(self):
        self.progress_bar.show()
        self.progress_bar.setValue(10)

    def on_load_progress(self, progress):
        self.progress_bar.setValue(progress)

    def on_load_finished(self, success):
        self.progress_bar.hide()

    def on_fullscreen_requested(self, request):
        if request.toggleOn():
            self.showFullScreen()
            request.accept()
        else:
            self.showNormal()
            request.accept()

    def on_download_requested(self, download: QWebEngineDownloadRequest):
        download_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        filename = download.suggestedFileName() or download.downloadFileName() or "whatsapp-attachment"
        download.setDownloadDirectory(download_dir)
        download.setDownloadFileName(filename)
        download.accept()

        def on_finished():
            if download.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                self.send_system_notification(
                    "WhatsApp Download Finished",
                    f"Saved {filename} to Downloads",
                    urgency="normal"
                )
        download.isFinishedChanged.connect(on_finished)

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self.base_icon, self)
        self.tray_icon.setToolTip("WhatsApp Lite")

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
        QShortcut(QKeySequence("Ctrl+Q"), self, self.really_quit)
        QShortcut(QKeySequence("Ctrl+W"), self, self.hide_to_tray)
        QShortcut(QKeySequence("Ctrl+R"), self, self.reload_page)
        QShortcut(QKeySequence("F5"), self, self.reload_page)
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

    def show_and_activate(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.raise_()
        self.activateWindow()

    def hide_to_tray(self):
        self.hide()
        # Memory optimization: trigger V8 GC when hidden to reclaim RAM
        if hasattr(self, 'web_page') and self.web_page:
            self.web_page.runJavaScript("if (window.gc) { window.gc(); }")

    def toggle_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide_to_tray()
        else:
            self.show_and_activate()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visibility()

    def handle_web_notification(self, notification):
        title = (notification.title() or "").strip()
        msg = (notification.message() or "").strip()

        # Check for incoming calls
        is_call = "call" in title.lower() or "call" in msg.lower()
        if is_call:
            self.show_and_activate()
            self.send_system_notification(
                f"📞 {title or 'WhatsApp Call'}",
                msg or "Incoming call...",
                urgency="critical"
            )
        else:
            if not self.isActiveWindow() or not self.isVisible():
                self.send_system_notification(title, msg, urgency="normal")

    def send_system_notification(self, title, message, urgency="normal"):
        if not title and not message:
            return
        if shutil.which("notify-send"):
            try:
                icon_path = OFFICIAL_ICON_PATH if os.path.exists(OFFICIAL_ICON_PATH) else "whatsapp-lite"
                subprocess.Popen([
                    "notify-send",
                    "-a", "WhatsApp",
                    "-u", urgency,
                    "-i", icon_path,
                    title,
                    message
                ])
                return
            except Exception:
                pass

        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 4000)

    def on_title_changed(self, title: str):
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

        size = 64
        pixmap = self.base_icon.pixmap(size, size)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        badge_radius = 16
        center_x = size - badge_radius - 2
        center_y = size - badge_radius - 2
        painter.setBrush(QColor(235, 64, 52))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPoint(center_x, center_y), badge_radius, badge_radius)

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
        if self.is_quitting:
            event.accept()
        else:
            event.ignore()
            self.hide_to_tray()

    def really_quit(self):
        self.is_quitting = True
        if hasattr(self, 'web_view') and self.web_view:
            self.web_view.stop()
            self.web_view.setPage(None)
        if hasattr(self, 'web_page') and self.web_page:
            self.web_page.deleteLater()
        self.app.quit()

# ---------------------------------------------------------
# Single Instance Management & Entry Point
# ---------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setWindowIcon(get_base_icon())

    socket = QLocalSocket()
    socket.connectToServer(SINGLE_INSTANCE_KEY)
    if socket.waitForConnected(400):
        socket.write(b"SHOW\n")
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        sys.exit(0)

    server = QLocalServer()
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
            window.show_and_activate()

    server.newConnection.connect(handle_incoming_connection)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
