from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import uuid
import os
import threading
import shlex
from pathlib import Path


from PySide6.QtCore import Qt, QSize, Signal, QUrl
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import (
    QColor,
    QFont,
    QMovie,
    QPainter,
    QPainterPath,
    QPixmap,
    QLinearGradient,
    QRadialGradient,
    QDesktopServices,
    QPen,
    QPalette,
    QShortcut,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .config import load_config, save_config
from .executor import execute_action

# ============================================================
# Desktop entry creation
# ============================================================

DESKTOP_DIR = Path.home() / ".local" / "share" / "applications"
DESKTOP_FILE = DESKTOP_DIR / "biohub.desktop"

def ensure_desktop_entry():
    """Create a .desktop file for BioHub if it doesn't exist."""
    if DESKTOP_FILE.exists():
        return

    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

    # Используем 'biohub' – команда, которая появится после установки
    content = f"""\
[Desktop Entry]
Type=Application
Name=BioHub
Comment=Personal command center
Exec=biohub %F
Icon=applications-utilities
Terminal=false
Categories=Utility;
StartupNotify=true
"""
    DESKTOP_FILE.write_text(content, encoding="utf-8")
    # Сделаем исполняемым (опционально)
    DESKTOP_FILE.chmod(0o644)


# ============================================================
# Paths
# ============================================================

DATA_DIR = Path.home() / ".local" / "share" / "hub"
ICONS_DIR = DATA_DIR / "icons"

SUPPORTED_IMAGES = {
    ".png", ".jpg", ".jpeg", ".gif",
    ".webp", ".bmp", ".ico", ".svg",
}


# ============================================================
# Theme constants
# ============================================================

CARD_SIZE_DEFAULT = 180
CARD_SIZE_MIN = 100
CARD_SIZE_MAX = 260

CARD_RADIUS_DEFAULT = 22
WINDOW_RADIUS = 28

WINDOW_MIN_WIDTH = 10
WINDOW_MIN_HEIGHT = 10
WINDOW_DEFAULT_WIDTH = 480
WINDOW_DEFAULT_HEIGHT = 440


# ============================================================
# Helpers
# ============================================================

def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)


def copy_icon_to_hub(source: str) -> str:
    """Copies an image into Hub's own icon directory."""
    ensure_dirs()
    source_path = Path(source)
    extension = source_path.suffix.lower()
    if extension not in SUPPORTED_IMAGES:
        raise ValueError("Unsupported image format.")
    target = ICONS_DIR / f"{uuid.uuid4().hex}{extension}"
    shutil.copy2(source_path, target)
    return str(target)


def remove_old_icon(path: str | None):
    if not path:
        return
    try:
        p = Path(path)
        if p.exists() and ICONS_DIR in p.parents:
            p.unlink()
    except OSError:
        pass


def get_image_path(icon: str | None) -> Path | None:
    if not icon:
        return None
    path = Path(icon).expanduser()
    if path.exists():
        return path
    candidate = ICONS_DIR / icon
    if candidate.exists():
        return candidate
    return None


def get_settings() -> dict:
    return load_config().get("settings", {})


def save_settings_patch(patch: dict):
    """Merge a few keys into settings without clobbering the rest."""
    config = load_config()
    settings = config.setdefault("settings", {})
    settings.update(patch)
    save_config(config)


def apply_dark_palette(app: QApplication):
    """
    Per-widget stylesheets don't reach every native control (combo box
    popups, message boxes, tooltips) — those fall back to the system
    theme, which is how you end up with white text on a white system
    theme. A palette set at the application level covers all of it.
    """
    palette = QPalette()

    dark = QColor(20, 22, 28)
    darker = QColor(12, 13, 18)
    text = QColor(238, 238, 239)
    muted = QColor(150, 150, 160)

    palette.setColor(QPalette.Window, dark)
    palette.setColor(QPalette.WindowText, text)
    palette.setColor(QPalette.Base, darker)
    palette.setColor(QPalette.AlternateBase, dark)
    palette.setColor(QPalette.ToolTipBase, dark)
    palette.setColor(QPalette.ToolTipText, text)
    palette.setColor(QPalette.Text, text)
    palette.setColor(QPalette.PlaceholderText, muted)
    palette.setColor(QPalette.Button, dark)
    palette.setColor(QPalette.ButtonText, text)
    palette.setColor(QPalette.BrightText, QColor(255, 90, 90))
    palette.setColor(QPalette.Highlight, QColor(255, 255, 255, 60))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.Text, muted)
    palette.setColor(QPalette.Disabled, QPalette.WindowText, muted)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, muted)

    app.setPalette(palette)


# ============================================================
# Monitors
# ============================================================

def list_monitors() -> list[dict]:
    """Returns the monitors Qt can see."""
    app = QApplication.instance()
    if not app:
        return []

    monitors = []
    primary = app.primaryScreen()

    for screen in app.screens():
        geo = screen.geometry()
        monitors.append({
            "name": screen.name(),
            "width": geo.width(),
            "height": geo.height(),
            "primary": screen is primary,
        })

    return monitors


def _detect_compositor() -> str | None:
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "hyprland"
    if os.environ.get("SWAYSOCK"):
        return "sway"
    return None


def focus_monitor(name: str | None):
    if not name:
        return
    compositor = _detect_compositor()
    try:
        if compositor == "hyprland":
            subprocess.run(
                ["hyprctl", "dispatch", f'hl.dsp.focus({{ monitor = "{name}" }})'],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        elif compositor == "sway":
            subprocess.run(
                ["swaymsg", "focus", "output", name],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
    except FileNotFoundError:
        pass


def _hyprland_window_addresses() -> set:
    try:
        result = subprocess.run(
            ["hyprctl", "clients", "-j"],
            check=False, capture_output=True, text=True, timeout=2,
        )
        data = json.loads(result.stdout or "[]")
        return {item.get("address") for item in data if item.get("address")}
    except Exception:
        return set()


def _sway_window_ids() -> set:
    try:
        result = subprocess.run(
            ["swaymsg", "-t", "get_tree"],
            check=False, capture_output=True, text=True, timeout=2,
        )
        tree = json.loads(result.stdout or "{}")
    except Exception:
        return set()

    ids = set()

    def walk(node):
        if not isinstance(node, dict):
            return
        if node.get("app_id") or node.get("window"):
            ids.add(node.get("id"))
        for child in node.get("nodes", []) + node.get("floating_nodes", []):
            walk(child)

    walk(tree)
    return ids


def snapshot_windows() -> dict:
    compositor = _detect_compositor()
    if compositor == "hyprland":
        return {"compositor": "hyprland", "ids": _hyprland_window_addresses()}
    if compositor == "sway":
        return {"compositor": "sway", "ids": _sway_window_ids()}
    return {"compositor": None, "ids": set()}


def _hyprland_clients() -> list[dict]:
    try:
        result = subprocess.run(
            ["hyprctl", "clients", "-j"],
            check=False, capture_output=True, text=True, timeout=2,
        )
        return json.loads(result.stdout or "[]")
    except Exception:
        return []


def _match_window_by_hint(hint: str, windows: list[dict]) -> dict | None:
    hint = (hint or "").lower()
    if not hint:
        return None
    for client in windows:
        cls = (client.get("class") or "").lower()
        title = (client.get("title") or "").lower()
        initial_class = (client.get("initialClass") or "").lower()
        if hint in cls or hint in title or hint in initial_class:
            return client
    return None


def _hyprland_monitor_id(name: str) -> int | None:
    try:
        result = subprocess.run(
            ["hyprctl", "monitors", "-j"],
            check=False, capture_output=True, text=True, timeout=2,
        )
        for m in json.loads(result.stdout or "[]"):
            if m.get("name") == name:
                return m.get("id")
    except Exception:
        pass
    return None


def _hyprland_workspace_on_monitor(monitor: str) -> str | None:
    try:
        result = subprocess.run(
            ["hyprctl", "monitors", "-j"],
            check=False, capture_output=True, text=True, timeout=2,
        )
        for m in json.loads(result.stdout or "[]"):
            if m.get("name") == monitor:
                ws = m.get("activeWorkspace") or {}
                wid = ws.get("id")
                if wid is not None:
                    return str(wid)
                if ws.get("name"):
                    return str(ws["name"])
    except Exception:
        pass
    return None


def _hyprland_move_window(addr: str, monitor: str):
    if not addr or not monitor:
        return

    print(f"[HUB] move {addr} → {monitor}", flush=True)

    # Hyprland 0.55+ Lua API
    cmds = [
        f'hl.dsp.window.move({{ monitor = "{monitor}", window = "address:{addr}" }})',
        f'hl.dsp.focus({{ window = "address:{addr}" }})',
        f'hl.dsp.window.move({{ monitor = "{monitor}" }})',
    ]

    ws = _hyprland_workspace_on_monitor(monitor)
    if ws:
        cmds.append(
            f'hl.dsp.window.move({{ workspace = "{ws}", window = "address:{addr}" }})'
        )

    for cmd in cmds:
        r = subprocess.run(
            ["hyprctl", "dispatch", cmd],
            check=False, capture_output=True, text=True, timeout=2,
        )
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        print(f"[HUB] hyprctl: {cmd!r} → out={out!r} err={err!r}", flush=True)
        time.sleep(0.04)


def place_new_windows_on_monitor(
    monitor: str,
    before: dict,
    timeout: float = 5.0,
    app_hint: str | None = None,
):
    if not monitor or before.get("compositor") not in ("hyprland", "sway"):
        return

    def _matches(client: dict, hint: str) -> bool:
        if not hint:
            return True
        h = hint.lower()
        for key in ("class", "initialClass", "title", "initialTitle"):
            val = (client.get(key) or "").lower()
            if h in val:
                return True
        if h == "brave" and "brave" in (client.get("class") or "").lower():
            return True
        if h == "zed" and "zed" in (client.get("class") or "").lower():
            return True
        return False

    def worker():
        compositor = before["compositor"]
        deadline = time.monotonic() + timeout
        moved = set()

        print(f"[HUB] place: monitor={monitor} hint={app_hint}", flush=True)

        while time.monotonic() < deadline:
            try:
                if compositor != "hyprland":
                    time.sleep(0.15)
                    continue

                clients = _hyprland_clients()
                current_addrs = {c.get("address") for c in clients if c.get("address")}
                new_addrs = current_addrs - before["ids"] - moved

                for client in clients:
                    addr = client.get("address")
                    if not addr or addr not in new_addrs:
                        continue
                    if app_hint and not _matches(client, app_hint):
                        continue
                    print(f"[HUB] move match class={client.get('class')} → {monitor}", flush=True)
                    _hyprland_move_window(addr, monitor)
                    moved.add(addr)

                if moved:
                    time.sleep(0.3)
                    continue
            except Exception as e:
                print(f"[HUB] place error: {e}", flush=True)
            time.sleep(0.15)

        if not moved and app_hint and compositor == "hyprland":
            try:
                clients = _hyprland_clients()
                for client in clients:
                    if _matches(client, app_hint) and client.get("address"):
                        print(f"[HUB] fallback move class={client.get('class')} → {monitor}", flush=True)
                        _hyprland_move_window(client["address"], monitor)
                        break
            except Exception as e:
                print(f"[HUB] fallback error: {e}", flush=True)

    threading.Thread(target=worker, daemon=True).start()


def _hyprland_exec_with_monitor(monitor: str, command_parts: list[str]):
    """Оставляем, но сейчас не используем в run_command."""
    cmd_str = " ".join(shlex.quote(p) for p in command_parts)
    rule = f"[monitor {monitor}] {cmd_str}"
    subprocess.Popen(
        ["hyprctl", "dispatch", "exec", rule],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


# ============================================================
# Glass Button
# ============================================================

class GlassButton(QPushButton):
    def __init__(self, text: str = "", parent: QWidget | None = None, accent: bool = False):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(36)

        if accent:
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,230);
                    color: #111318;
                    border: none;
                    border-radius: 11px;
                    padding: 0 16px;
                    font-weight: 600;
                }
                QPushButton:hover { background: rgba(255,255,255,255); }
                QPushButton:pressed { background: rgba(220,220,225,230); }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,12);
                    color: #eeeeef;
                    border: 1px solid rgba(255,255,255,22);
                    border-radius: 11px;
                    padding: 0 14px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,22);
                    border-color: rgba(255,255,255,40);
                }
                QPushButton:pressed { background: rgba(255,255,255,30); }
            """)


# ============================================================
# Command Card  (Steam Deck style — image IS the button)
# ============================================================

class CommandCard(QFrame):
    clicked = Signal()
    edit_requested = Signal()
    delete_requested = Signal()

    def __init__(
        self,
        name: str,
        command: dict,
        manage_mode: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.name = name
        self.command = command
        self.manage_mode = manage_mode
        self.hovered = False
        self.pressed = False
        self.movie: QMovie | None = None

        settings = get_settings()
        self.card_size = int(settings.get("card_size", CARD_SIZE_DEFAULT))
        self.card_size = max(CARD_SIZE_MIN, min(CARD_SIZE_MAX, self.card_size))

        self.setFixedSize(self.card_size, self.card_size)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.PointingHandCursor)

        self.load_media()

    def load_media(self):
        icon = self.command.get("icon")
        path = get_image_path(icon)
        if not path:
            return
        if path.suffix.lower() == ".gif":
            movie = QMovie(str(path))
            if movie.isValid():
                movie.setScaledSize(QSize(self.card_size, self.card_size))
                movie.frameChanged.connect(self.update)
                movie.start()
                self.movie = movie

    # ---- mouse ----
    def enterEvent(self, event):
        self.hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.pressed = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            inside = self.rect().contains(event.position().toPoint())
            self.pressed = False
            self.update()
            if inside:
                if self.manage_mode:
                    self.edit_requested.emit()
                else:
                    self.clicked.emit()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.manage_mode:
            self.edit_requested.emit()
        super().mouseDoubleClickEvent(event)

    # ---- painting helpers ----
    def draw_image_cover(self, painter: QPainter, pixmap: QPixmap):
        if pixmap.isNull():
            return
        target = self.rect()
        scaled = pixmap.scaled(
            target.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        x = (scaled.width() - target.width()) // 2
        y = (scaled.height() - target.height()) // 2
        cropped = scaled.copy(x, y, target.width(), target.height())
        painter.drawPixmap(0, 0, cropped)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        settings = get_settings()
        radius = int(settings.get("card_radius", CARD_RADIUS_DEFAULT))
        size = self.card_size

        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.setClipPath(path)

        icon = self.command.get("icon")
        image_path = get_image_path(icon)
        has_image = image_path is not None

        # scaled type sizes so small/large icons stay legible
        title_pt = max(10, size // 13)
        desc_pt = max(8, size // 20)
        emoji_pt = max(20, size // 4)
        badge = max(22, size // 7)

        # ========== IMAGE BUTTON ==========
        if has_image:
            if self.movie and self.movie.isValid():
                pixmap = self.movie.currentPixmap()
            else:
                pixmap = QPixmap(str(image_path))

            self.draw_image_cover(painter, pixmap)

            # liquid-glass sheen across the surface
            sheen = QLinearGradient(0, 0, self.width(), self.height())
            sheen.setColorAt(0.0, QColor(255, 255, 255, 30))
            sheen.setColorAt(0.45, QColor(255, 255, 255, 0))
            painter.fillRect(self.rect(), sheen)

            gradient = QLinearGradient(0, self.height() * 0.45, 0, self.height())
            gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
            gradient.setColorAt(0.55, QColor(0, 0, 0, 80))
            gradient.setColorAt(1.0, QColor(0, 0, 0, 210))
            painter.fillRect(self.rect(), gradient)

            if self.pressed:
                painter.fillRect(self.rect(), QColor(0, 0, 0, 50))
            elif self.hovered:
                painter.fillRect(self.rect(), QColor(255, 255, 255, 28))

        # ========== EMOJI / GLASS BUTTON ==========
        else:
            painter.fillPath(path, QColor(255, 255, 255, 10))
            painter.fillPath(path, QColor(18, 20, 28, 160))

            sheen = QLinearGradient(0, 0, self.width(), self.height())
            sheen.setColorAt(0.0, QColor(255, 255, 255, 26))
            sheen.setColorAt(0.5, QColor(255, 255, 255, 0))
            painter.fillPath(path, sheen)

            if self.hovered:
                painter.fillPath(path, QColor(255, 255, 255, 22))
            if self.pressed:
                painter.fillPath(path, QColor(0, 0, 0, 40))

            emoji = icon or "📌"
            emoji_font = QFont()
            emoji_font.setPointSize(emoji_pt)
            painter.setFont(emoji_font)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(
                self.rect().adjusted(0, -int(size * 0.1), 0, 0),
                Qt.AlignCenter,
                emoji,
            )

        # ========== TEXT ==========
        title = self.name
        description = self.command.get("description", "")

        title_font = QFont()
        title_font.setPointSize(title_pt)
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(QColor(255, 255, 255))

        if has_image:
            title_bottom = max(22, int(size * 0.17))
            desc_bottom = max(10, int(size * 0.06))

            title_rect = self.rect().adjusted(12, 0, -12, -title_bottom)
            painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignBottom, title)

            if description:
                desc_font = QFont()
                desc_font.setPointSize(desc_pt)
                painter.setFont(desc_font)
                painter.setPen(QColor(220, 220, 225, 200))
                desc_rect = self.rect().adjusted(12, 0, -12, -desc_bottom)
                painter.drawText(desc_rect, Qt.AlignLeft | Qt.AlignBottom, description)
        else:
            top_pad = int(size * 0.39)
            bottom_pad = int(size * 0.21)
            title_rect = self.rect().adjusted(10, top_pad, -10, -bottom_pad)
            painter.drawText(title_rect, Qt.AlignCenter, title)

            if description:
                desc_font = QFont()
                desc_font.setPointSize(desc_pt)
                painter.setFont(desc_font)
                painter.setPen(QColor(170, 170, 180))
                desc_top = int(size * 0.56)
                desc_bottom = int(size * 0.08)
                desc_rect = self.rect().adjusted(10, desc_top, -10, -desc_bottom)
                painter.drawText(desc_rect, Qt.AlignCenter, description)

        # ========== MANAGE OVERLAY ==========
        if self.manage_mode:
            painter.fillPath(path, QColor(0, 0, 0, 70))

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 235))
            painter.drawEllipse(self.width() - badge - 12, 10, badge, badge)
            painter.setPen(QColor(25, 25, 30))
            font = QFont()
            font.setPointSize(max(11, badge // 2))
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(self.width() - badge - 12, 10, badge, badge, Qt.AlignCenter, "✎")

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 70, 70, 235))
            painter.drawEllipse(self.width() - badge - 12, 14 + badge, badge, badge)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(self.width() - badge - 12, 14 + badge, badge, badge, Qt.AlignCenter, "×")

        # ========== OUTER BORDER ==========
        painter.setClipping(False)
        border_color = (
            QColor(255, 255, 255, 70) if self.hovered
            else QColor(255, 255, 255, 28)
        )
        pen = QPen(border_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)


# ============================================================
# Action Editor
# ============================================================

class ActionEditor(QFrame):
    def __init__(self, action: dict | None = None, parent: QWidget | None = None):
        super().__init__(parent)

        self.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,8);
                border: 1px solid rgba(255,255,255,16);
                border-radius: 14px;
            }
            QLineEdit, QComboBox, QTextEdit {
                background: rgba(0,0,0,55);
                color: #eeeeef;
                border: 1px solid rgba(255,255,255,20);
                border-radius: 9px;
                padding: 7px 10px;
                selection-background-color: #3a3d45;
            }
            QComboBox QAbstractItemView {
                background: #1c1e26;
                color: white;
                selection-background-color: #3a3d45;
                border: 1px solid rgba(255,255,255,20);
            }
            QLabel { color: #a1a1aa; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(9)

        top = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["browser", "app"])
        self.monitor_combo = QComboBox()
        self.monitor_combo.addItem("Same monitor as Hub", "")
        for monitor in list_monitors():
            label = f"{monitor['name']} ({monitor['width']}×{monitor['height']})"
            if monitor["primary"]:
                label += " • primary"
            self.monitor_combo.addItem(label, monitor["name"])
        self.remove_button = GlassButton("Remove")
        top.addWidget(self.type_combo)
        top.addWidget(self.monitor_combo, 1)
        top.addWidget(self.remove_button)
        layout.addLayout(top)

        self.content = QVBoxLayout()
        self.content.setSpacing(8)
        layout.addLayout(self.content)

        self.type_combo.currentTextChanged.connect(self.update_content)
        self.remove_button.clicked.connect(self.deleteLater)

        self.action = action or {"type": "browser", "urls": []}
        self.type_combo.setCurrentText(self.action.get("type", "browser"))
        monitor_idx = self.monitor_combo.findData(self.action.get("monitor", ""))
        if monitor_idx >= 0:
            self.monitor_combo.setCurrentIndex(monitor_idx)
        self.update_content()

    def clear_layout(self):
        while self.content.count():
            item = self.content.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def update_content(self):
        self.clear_layout()
        action_type = self.type_combo.currentText()

        if action_type == "browser":
            label = QLabel("URLs")
            self.content.addWidget(label)

            self.urls_edit = QTextEdit()
            urls = self.action.get("urls", [])
            self.urls_edit.setPlainText("\n".join(urls))
            self.urls_edit.setFixedHeight(75)
            self.content.addWidget(self.urls_edit)

            self.browser_edit = QLineEdit(self.action.get("browser", "brave"))
            self.browser_edit.setPlaceholderText("Browser command, e.g. brave")
            self.content.addWidget(self.browser_edit)
        else:
            label = QLabel("Application command")
            self.content.addWidget(label)

            self.command_edit = QLineEdit(self.action.get("command", ""))
            self.command_edit.setPlaceholderText("Example: zed")
            self.content.addWidget(self.command_edit)

    def to_dict(self) -> dict:
        action_type = self.type_combo.currentText()
        monitor = self.monitor_combo.currentData() or ""
        if action_type == "browser":
            urls = [
                line.strip()
                for line in self.urls_edit.toPlainText().splitlines()
                if line.strip()
            ]
            return {
                "type": "browser",
                "urls": urls,
                "browser": self.browser_edit.text().strip() or "brave",
                "monitor": monitor,
            }
        return {
            "type": "app",
            "command": self.command_edit.text().strip(),
            "monitor": monitor,
        }


# ============================================================
# Icon Preview
# ============================================================

class IconPreview(QFrame):
    """Small live preview of the currently chosen image or emoji."""

    def __init__(self, icon: str | None, parent: QWidget | None = None):
        super().__init__(parent)
        self.icon = icon
        self.setFixedSize(76, 76)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def set_icon(self, icon: str | None):
        self.icon = icon
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)
        painter.setClipPath(path)

        image_path = get_image_path(self.icon)

        if image_path:
            pixmap = QPixmap(str(image_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                x = (scaled.width() - self.width()) // 2
                y = (scaled.height() - self.height()) // 2
                painter.drawPixmap(0, 0, scaled.copy(x, y, self.width(), self.height()))
            else:
                self._draw_placeholder(painter)
        elif self.icon:
            painter.fillPath(path, QColor(255, 255, 255, 12))
            font = QFont()
            font.setPointSize(28)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(self.rect(), Qt.AlignCenter, self.icon)
        else:
            self._draw_placeholder(painter)

        painter.setClipping(False)
        pen = QPen(QColor(255, 255, 255, 40))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

    def _draw_placeholder(self, painter: QPainter):
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)
        painter.fillPath(path, QColor(255, 255, 255, 8))
        font = QFont()
        font.setPointSize(24)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 90))
        painter.drawText(self.rect(), Qt.AlignCenter, "?")


# ============================================================
# Emoji Picker
# ============================================================

COMMON_EMOJIS = [
    "🚀", "💻", "🌐", "🎮", "📚", "🎬", "🎵", "📧", "💬", "🖥️",
    "📁", "⚙️", "🔧", "📝", "🎨", "📷", "🗓️", "🔒", "☁️", "🧠",
    "🛠️", "📦", "🧩", "⌨️", "🛰️", "🧪", "📊", "🕹️", "🎧", "📺",
    "🔍", "🗂️", "🧭", "🔥", "⭐", "❤️", "☕", "🍿", "🎯", "📌",
]


class EmojiPickerDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Choose Emoji")
        self.resize(420, 400)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.old_pos = None
        self.selected: str | None = None
        self.build_ui()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)

        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background: rgba(14,16,22,235);
                border: 1px solid rgba(255,255,255,28);
                border-radius: 22px;
            }
        """)
        root.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Choose an emoji")
        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
        title.setStyleSheet("color: #eeeeef;")
        header.addWidget(title)
        header.addStretch()
        close = GlassButton("×")
        close.setFixedSize(32, 30)
        close.clicked.connect(self.reject)
        header.addWidget(close)
        layout.addLayout(header)

        grid_frame = QFrame()
        grid = QGridLayout(grid_frame)
        grid.setSpacing(6)

        columns = 8
        for i, emoji in enumerate(COMMON_EMOJIS):
            button = QPushButton(emoji)
            button.setFixedSize(42, 42)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,10);
                    border: 1px solid rgba(255,255,255,18);
                    border-radius: 10px;
                    font-size: 18px;
                }
                QPushButton:hover { background: rgba(255,255,255,22); }
            """)
            button.clicked.connect(lambda checked=False, e=emoji: self._choose(e))
            grid.addWidget(button, i // columns, i % columns)

        layout.addWidget(grid_frame)

        custom_row = QHBoxLayout()
        custom_label = QLabel("Or type your own:")
        custom_label.setStyleSheet("color: #a1a1aa;")
        self.custom_edit = QLineEdit()
        self.custom_edit.setPlaceholderText("Paste an emoji")
        self.custom_edit.setMaxLength(8)
        self.custom_edit.setStyleSheet("""
            QLineEdit {
                background: rgba(0,0,0,55);
                color: #eeeeef;
                border: 1px solid rgba(255,255,255,22);
                border-radius: 10px;
                padding: 6px 10px;
            }
        """)
        use_button = GlassButton("Use")
        use_button.clicked.connect(self._use_custom)
        custom_row.addWidget(custom_label)
        custom_row.addWidget(self.custom_edit, 1)
        custom_row.addWidget(use_button)
        layout.addLayout(custom_row)

    def _choose(self, emoji: str):
        self.selected = emoji
        self.accept()

    def _use_custom(self):
        text = self.custom_edit.text().strip()
        if text:
            self.selected = text
            self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            current = event.globalPosition().toPoint()
            delta = current - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = current

    def mouseReleaseEvent(self, event):
        self.old_pos = None


# ============================================================
# Command Editor
# ============================================================

class CommandEditor(QDialog):
    saved = Signal()

    def __init__(self, name: str | None = None, command: dict | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.original_name = name
        self.command = command or {}

        self.setWindowTitle("Edit Command" if name else "New Command")
        self.resize(680, 720)
        self.setMinimumSize(620, 650)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setStyleSheet("""
            QDialog { background: transparent; }
            QLabel { color: #eeeeef; }
            QLineEdit, QTextEdit {
                background: rgba(0,0,0,55);
                color: #eeeeef;
                border: 1px solid rgba(255,255,255,22);
                border-radius: 11px;
                padding: 9px 11px;
                selection-background-color: #3a3d45;
            }
            QLineEdit:focus, QTextEdit:focus { border-color: rgba(255,255,255,55); }
            QScrollArea { background: transparent; border: none; }
            QCheckBox { color: #dddddf; }
        """)

        self.build_ui()
        self.old_pos = None

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)

        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background: rgba(14,16,22,230);
                border: 1px solid rgba(255,255,255,28);
                border-radius: 24px;
            }
        """)
        root.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Edit Command" if self.original_name else "New Command")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
        header.addWidget(title)
        header.addStretch()
        close = GlassButton("×")
        close.setFixedSize(40, 36)
        close.clicked.connect(self.reject)
        header.addWidget(close)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(2, 2, 2, 2)
        content_layout.setSpacing(16)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        section = QLabel("GENERAL")
        section.setStyleSheet("color: #777b86; font-size: 11px; font-weight: 700;")
        content_layout.addWidget(section)

        self.name_edit = QLineEdit(self.original_name or "")
        self.name_edit.setPlaceholderText("Command name")
        content_layout.addWidget(self.name_edit)

        self.description_edit = QLineEdit(self.command.get("description", ""))
        self.description_edit.setPlaceholderText("Short description")
        content_layout.addWidget(self.description_edit)

        icon_title = QLabel("ICON")
        icon_title.setStyleSheet("color: #777b86; font-size: 11px; font-weight: 700;")
        content_layout.addWidget(icon_title)

        icon_row = QHBoxLayout()
        icon_row.setSpacing(14)

        self._icon_value = self.command.get("icon", "📌")
        self.icon_preview = IconPreview(self._icon_value)
        icon_row.addWidget(self.icon_preview)

        icon_buttons = QVBoxLayout()
        icon_buttons.setSpacing(6)

        browse = GlassButton("Browse image...")
        browse.clicked.connect(self.choose_image)

        emoji_button = GlassButton("Choose emoji...")
        emoji_button.clicked.connect(self.choose_emoji)

        clear_button = GlassButton("Clear icon")
        clear_button.clicked.connect(self.clear_icon)

        icon_buttons.addWidget(browse)
        icon_buttons.addWidget(emoji_button)
        icon_buttons.addWidget(clear_button)

        icon_row.addLayout(icon_buttons)
        icon_row.addStretch()
        content_layout.addLayout(icon_row)

        self.icon_info = QLabel("Images: PNG, JPG, GIF, WEBP, BMP, ICO, SVG — or pick an emoji instead.")
        self.icon_info.setStyleSheet("color: #777b86; font-size: 11px;")
        content_layout.addWidget(self.icon_info)

        actions_title = QLabel("ACTIONS")
        actions_title.setStyleSheet("color: #777b86; font-size: 11px; font-weight: 700;")
        content_layout.addWidget(actions_title)

        self.actions_container = QVBoxLayout()
        self.actions_container.setSpacing(10)
        content_layout.addLayout(self.actions_container)

        add_action = GlassButton("+ Add action")
        add_action.clicked.connect(lambda: self.add_action())
        content_layout.addWidget(add_action)
        content_layout.addStretch()

        for action in self.command.get("actions", []):
            self.add_action(action)

        if not self.command.get("actions"):
            self.add_action({"type": "browser", "urls": [], "browser": "brave"})

        buttons = QHBoxLayout()
        cancel = GlassButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = GlassButton("Save Command", accent=True)
        save.clicked.connect(self.save)
        buttons.addWidget(cancel)
        buttons.addStretch()
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            current = event.globalPosition().toPoint()
            delta = current - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = current

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def add_action(self, action=None):
        editor = ActionEditor(action, self)
        self.actions_container.addWidget(editor)

    def choose_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose image", str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.gif *.webp *.bmp *.ico *.svg)",
        )
        if not path:
            return
        try:
            copied = copy_icon_to_hub(path)
            self._icon_value = copied
            self.icon_preview.set_icon(copied)
        except Exception as exc:
            QMessageBox.critical(self, "Image error", str(exc))

    def choose_emoji(self):
        dialog = EmojiPickerDialog(self)
        if dialog.exec() == QDialog.Accepted and dialog.selected:
            self._icon_value = dialog.selected
            self.icon_preview.set_icon(dialog.selected)

    def clear_icon(self):
        self._icon_value = "📌"
        self.icon_preview.set_icon(self._icon_value)

    def save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Enter a command name.")
            return

        config = load_config()
        commands = config.setdefault("commands", {})

        if name != self.original_name and name in commands:
            QMessageBox.warning(self, "Already exists", f"Command '{name}' already exists.")
            return

        actions = []
        for i in range(self.actions_container.count()):
            item = self.actions_container.itemAt(i)
            widget = item.widget()
            if isinstance(widget, ActionEditor):
                actions.append(widget.to_dict())

        command = {
            "description": self.description_edit.text().strip(),
            "actions": actions,
            "icon": self._icon_value or "📌",
        }

        if self.original_name:
            commands.pop(self.original_name, None)

        commands[name] = command
        save_config(config)
        self.saved.emit()
        self.accept()


# ============================================================
# Settings Window  (fully dark)
# ============================================================

class SettingsWindow(QDialog):
    settings_saved = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Hub Settings")
        self.resize(760, 540)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.old_pos = None

        self.setStyleSheet("""
            QDialog { background: transparent; }
            QLabel { color: #eeeeef; }
            QCheckBox { color: #dddddf; spacing: 8px; }
            QCheckBox::indicator {
                width: 18px; height: 18px; border-radius: 5px;
                border: 1px solid rgba(255,255,255,30);
                background: rgba(0,0,0,50);
            }
            QCheckBox::indicator:checked {
                background: rgba(255,255,255,200);
                border-color: rgba(255,255,255,80);
            }
            QSlider::groove:horizontal {
                height: 6px; background: rgba(255,255,255,18); border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 18px; height: 18px; margin: -6px 0;
                background: white; border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: rgba(255,255,255,80); border-radius: 3px;
            }
            QSpinBox {
                background: rgba(0,0,0,55); color: white;
                border: 1px solid rgba(255,255,255,22);
                border-radius: 9px; padding: 6px 10px;
            }
        """)

        self.build_ui()
        self.load_settings()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background: rgba(14,16,22,235);
                border: 1px solid rgba(255,255,255,28);
                border-radius: 24px;
            }
        """)
        root.addWidget(panel)

        main = QHBoxLayout(panel)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        sidebar = QFrame()
        sidebar.setFixedWidth(190)
        sidebar.setStyleSheet("""
            QFrame { background: rgba(255,255,255,7); border-radius: 18px; }
        """)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 18, 12, 12)
        side_layout.setSpacing(5)

        title = QLabel("HUB")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
        title.setContentsMargins(10, 0, 0, 16)
        side_layout.addWidget(title)

        self.nav_buttons = []
        for text in ["Appearance", "Behavior", "Displays", "Storage", "About"]:
            button = QPushButton(text)
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet("""
                QPushButton {
                    text-align: left; color: #a1a1aa; background: transparent;
                    border: none; border-radius: 10px; padding: 10px 12px;
                }
                QPushButton:hover { background: rgba(255,255,255,10); color: white; }
                QPushButton:checked { background: rgba(255,255,255,18); color: white; }
            """)
            side_layout.addWidget(button)
            self.nav_buttons.append(button)

        side_layout.addStretch()
        main.addWidget(sidebar)

        right = QVBoxLayout()
        self.pages = QStackedWidget()
        self.pages.addWidget(self.appearance_page())
        self.pages.addWidget(self.behavior_page())
        self.pages.addWidget(self.displays_page())
        self.pages.addWidget(self.storage_page())
        self.pages.addWidget(self.about_page())
        right.addWidget(self.pages)

        bottom = QHBoxLayout()
        close = GlassButton("Cancel")
        close.clicked.connect(self.reject)
        save = GlassButton("Save", accent=True)
        save.clicked.connect(self.save_settings)
        bottom.addWidget(close)
        bottom.addStretch()
        bottom.addWidget(save)
        right.addLayout(bottom)

        main.addLayout(right, 1)

        for index, button in enumerate(self.nav_buttons):
            button.clicked.connect(lambda checked=False, i=index: self.pages.setCurrentIndex(i))
        self.nav_buttons[0].setChecked(True)

    def make_page(self, title: str, subtitle: str):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 14, 20, 10)

        heading = QLabel(title)
        font = QFont()
        font.setPointSize(21)
        font.setWeight(QFont.Weight.DemiBold)
        heading.setFont(font)
        layout.addWidget(heading)

        sub = QLabel(subtitle)
        sub.setStyleSheet("color: #777b86;")
        layout.addWidget(sub)
        layout.addSpacing(20)
        return page, layout

    def appearance_page(self):
        page, layout = self.make_page("Appearance", "Customize how Hub looks.")

        opacity_row = QHBoxLayout()
        label = QLabel("Glass opacity")
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 245)
        self.opacity_value = QLabel()
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_value.setText(str(v)))
        opacity_row.addWidget(label)
        opacity_row.addWidget(self.opacity_slider, 1)
        opacity_row.addWidget(self.opacity_value)
        layout.addLayout(opacity_row)
        layout.addSpacing(18)

        icon_size_row = QHBoxLayout()
        icon_size_label = QLabel("Icon size")
        self.icon_size_slider = QSlider(Qt.Horizontal)
        self.icon_size_slider.setRange(CARD_SIZE_MIN, CARD_SIZE_MAX)
        self.icon_size_value = QLabel()
        self.icon_size_slider.valueChanged.connect(
            lambda v: self.icon_size_value.setText(f"{v} px")
        )
        icon_size_row.addWidget(icon_size_label)
        icon_size_row.addWidget(self.icon_size_slider, 1)
        icon_size_row.addWidget(self.icon_size_value)
        layout.addLayout(icon_size_row)
        layout.addSpacing(18)

        radius_row = QHBoxLayout()
        radius_label = QLabel("Card radius")
        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(10, 40)
        self.radius_spin.setSuffix(" px")
        radius_row.addWidget(radius_label)
        radius_row.addStretch()
        radius_row.addWidget(self.radius_spin)
        layout.addLayout(radius_row)
        layout.addSpacing(24)

        size_title = QLabel("WINDOW SIZE")
        size_title.setStyleSheet("color: #777b86; font-size: 11px; font-weight: 700;")
        layout.addWidget(size_title)
        layout.addSpacing(6)

        size_row = QHBoxLayout()

        width_label = QLabel("Width")
        self.width_spin = QSpinBox()
        self.width_spin.setRange(WINDOW_MIN_WIDTH, 1000)
        self.width_spin.setSuffix(" px")
        self.width_spin.setSingleStep(10)

        height_label = QLabel("Height")
        self.height_spin = QSpinBox()
        self.height_spin.setRange(WINDOW_MIN_HEIGHT, 1000)
        self.height_spin.setSuffix(" px")
        self.height_spin.setSingleStep(10)

        size_row.addWidget(width_label)
        size_row.addWidget(self.width_spin)
        size_row.addSpacing(18)
        size_row.addWidget(height_label)
        size_row.addWidget(self.height_spin)
        size_row.addStretch()
        layout.addLayout(size_row)

        layout.addSpacing(10)

        preset_row = QHBoxLayout()
        preset_label = QLabel("Presets:")
        preset_label.setStyleSheet("color: #777b86;")
        preset_row.addWidget(preset_label)

        for label, (w, h) in (
            ("Compact", (WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)),
            ("Default", (WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)),
            ("Large", (680, 700)),
        ):
            preset_button = GlassButton(label)
            preset_button.clicked.connect(
                lambda checked=False, w=w, h=h: self._apply_size_preset(w, h)
            )
            preset_row.addWidget(preset_button)

        preset_row.addStretch()
        layout.addLayout(preset_row)

        layout.addStretch()
        return page

    def _apply_size_preset(self, width: int, height: int):
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)

    def behavior_page(self):
        page, layout = self.make_page("Behavior", "Control how Hub behaves on your desktop.")
        self.always_on_top = QCheckBox("Always keep Hub on top")
        self.center_window = QCheckBox("Center Hub when opened")
        self.close_after_action = QCheckBox("Hide Hub after launching a command")
        layout.addWidget(self.always_on_top)
        layout.addWidget(self.center_window)
        layout.addWidget(self.close_after_action)
        layout.addStretch()
        return page

    def displays_page(self):
        page, layout = self.make_page(
            "Displays",
            "Monitors Hub has detected. Pick which one each action opens on "
            "from the Actions section when you edit a command.",
        )

        monitors = list_monitors()

        if not monitors:
            empty = QLabel("No displays detected.")
            empty.setStyleSheet("color: #777b86;")
            layout.addWidget(empty)
        else:
            for monitor in monitors:
                text = f"{monitor['name']}  —  {monitor['width']}×{monitor['height']}"
                if monitor["primary"]:
                    text += "  (primary)"

                row = QLabel(text)
                row.setStyleSheet("""
                    QLabel {
                        background: rgba(0,0,0,45);
                        border: 1px solid rgba(255,255,255,16);
                        border-radius: 12px;
                        padding: 12px;
                        color: #dcdce0;
                    }
                """)
                layout.addWidget(row)

        layout.addSpacing(12)

        note = QLabel(
            "Per-action monitor targeting works out of the box on Hyprland "
            "and Sway. Other window managers don't expose a generic way to "
            "do this, so the action will just open on whichever monitor is "
            "currently focused."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #777b86; font-size: 11px;")
        layout.addWidget(note)

        layout.addStretch()
        return page

    def storage_page(self):
        page, layout = self.make_page("Storage", "Where Hub stores its configuration and icons.")

        config_label = QLabel(f"Config\n{Path.home() / '.config' / 'hub' / 'config.yaml'}")
        config_label.setStyleSheet("""
            QLabel {
                background: rgba(0,0,0,45); border: 1px solid rgba(255,255,255,16);
                border-radius: 12px; padding: 12px; color: #b4b4bd;
            }
        """)
        layout.addWidget(config_label)

        icons_label = QLabel(f"Icons\n{ICONS_DIR}")
        icons_label.setStyleSheet("""
            QLabel {
                background: rgba(0,0,0,45); border: 1px solid rgba(255,255,255,16);
                border-radius: 12px; padding: 12px; color: #b4b4bd;
            }
        """)
        layout.addWidget(icons_label)

        open_folder = GlassButton("Open icons folder")
        open_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(ICONS_DIR))))
        layout.addWidget(open_folder)
        layout.addStretch()
        return page

    def about_page(self):
        page, layout = self.make_page("About Hub", "A small command center for your desktop.")
        text = QLabel(
            "HUB\n\n"
            "Launch applications, websites and workflows "
            "from one beautiful desktop interface.\n\n"
            "Built with Python + PySide6."
        )
        text.setStyleSheet("""
            QLabel {
                color: #b4b4bd; background: rgba(255,255,255,7);
                border: 1px solid rgba(255,255,255,14); border-radius: 16px; padding: 20px;
            }
        """)
        layout.addWidget(text)
        layout.addStretch()
        return page

    def load_settings(self):
        settings = get_settings()
        self.opacity_slider.setValue(int(settings.get("glass_opacity", 190)))
        self.opacity_value.setText(str(self.opacity_slider.value()))

        icon_size = int(settings.get("card_size", CARD_SIZE_DEFAULT))
        icon_size = max(CARD_SIZE_MIN, min(CARD_SIZE_MAX, icon_size))
        self.icon_size_slider.setValue(icon_size)
        self.icon_size_value.setText(f"{icon_size} px")

        self.radius_spin.setValue(int(settings.get("card_radius", CARD_RADIUS_DEFAULT)))

        width = int(settings.get("window_width", WINDOW_DEFAULT_WIDTH))
        height = int(settings.get("window_height", WINDOW_DEFAULT_HEIGHT))
        self.width_spin.setValue(max(WINDOW_MIN_WIDTH, min(1000, width)))
        self.height_spin.setValue(max(WINDOW_MIN_HEIGHT, min(1000, height)))

        self.always_on_top.setChecked(settings.get("always_on_top", True))
        self.center_window.setChecked(settings.get("center_window", True))
        self.close_after_action.setChecked(settings.get("close_after_action", False))

    def save_settings(self):
        config = load_config()
        existing = config.get("settings", {})
        config["settings"] = {
            **existing,
            "glass_opacity": self.opacity_slider.value(),
            "card_size": self.icon_size_slider.value(),
            "card_radius": self.radius_spin.value(),
            "window_width": self.width_spin.value(),
            "window_height": self.height_spin.value(),
            "always_on_top": self.always_on_top.isChecked(),
            "center_window": self.center_window.isChecked(),
            "close_after_action": self.close_after_action.isChecked(),
        }
        save_config(config)
        self.settings_saved.emit()
        self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            current = event.globalPosition().toPoint()
            delta = current - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = current

    def mouseReleaseEvent(self, event):
        self.old_pos = None


# ============================================================
# Manage Window
# ============================================================

class ManageWindow(QDialog):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Manage Commands")
        self.resize(600, 500)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.old_pos = None
        self.build_ui()
        self.refresh()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background: rgba(14,16,22,235);
                border: 1px solid rgba(255,255,255,28);
                border-radius: 24px;
            }
            QListWidget {
                background: rgba(0,0,0,40);
                border: 1px solid rgba(255,255,255,16);
                border-radius: 14px;
                padding: 6px;
                color: white;
                outline: none;
            }
            QListWidget::item { padding: 12px; border-radius: 9px; }
            QListWidget::item:hover { background: rgba(255,255,255,12); }
            QListWidget::item:selected { background: rgba(255,255,255,20); }
        """)
        root.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 20, 22, 20)

        header = QHBoxLayout()
        title = QLabel("Commands")
        font = QFont()
        font.setPointSize(20)
        font.setWeight(QFont.Weight.DemiBold)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()
        close = GlassButton("×")
        close.setFixedSize(40, 36)
        close.clicked.connect(self.accept)
        header.addWidget(close)
        layout.addLayout(header)

        self.list = QListWidget()
        layout.addWidget(self.list)

        buttons = QHBoxLayout()
        add = GlassButton("+ Add")
        edit = GlassButton("Edit")
        delete = GlassButton("Delete")
        buttons.addWidget(add)
        buttons.addWidget(edit)
        buttons.addWidget(delete)
        buttons.addStretch()
        done = GlassButton("Done", accent=True)
        buttons.addWidget(done)
        layout.addLayout(buttons)

        add.clicked.connect(self.add_command)
        edit.clicked.connect(self.edit_command)
        delete.clicked.connect(self.delete_command)
        done.clicked.connect(self.accept)
        self.list.itemDoubleClicked.connect(lambda _: self.edit_command())

    def refresh(self):
        self.list.clear()
        config = load_config()
        for name in config.get("commands", {}):
            item = QListWidgetItem(name)
            self.list.addItem(item)

    def add_command(self):
        editor = CommandEditor(parent=self)
        editor.saved.connect(self.on_changed)
        editor.exec()

    def edit_command(self):
        item = self.list.currentItem()
        if not item:
            return
        name = item.text()
        config = load_config()
        command = config.get("commands", {}).get(name, {})
        editor = CommandEditor(name, command, self)
        editor.saved.connect(self.on_changed)
        editor.exec()

    def delete_command(self):
        item = self.list.currentItem()
        if not item:
            return
        name = item.text()
        result = QMessageBox.question(self, "Delete command", f"Delete '{name}'?")
        if result != QMessageBox.Yes:
            return

        config = load_config()
        command = config.get("commands", {}).get(name, {})
        remove_old_icon(command.get("icon"))
        config.get("commands", {}).pop(name, None)
        save_config(config)
        self.on_changed()

    def on_changed(self):
        self.refresh()
        self.changed.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            current = event.globalPosition().toPoint()
            delta = current - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = current

    def mouseReleaseEvent(self, event):
        self.old_pos = None


# ============================================================
# Main Hub Window
# ============================================================

class HubWindow(QWidget):

    RESIZE_MARGIN = 8

    def __init__(self):
        super().__init__()

        self.drag_position = None
        self.resize_edges = None
        self.resize_start_geo = None
        self.resize_start_pos = None
        self.manage_mode = False

        self.setWindowTitle("Hub")
        self.setObjectName("HubWindow")

        settings = get_settings()
        self.setWindowFlags(self._build_flags(settings))
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        width = int(settings.get("window_width", WINDOW_DEFAULT_WIDTH))
        height = int(settings.get("window_height", WINDOW_DEFAULT_HEIGHT))
        width = max(WINDOW_MIN_WIDTH, min(1000, width))
        height = max(WINDOW_MIN_HEIGHT, min(1000, height))
        # setFixedSize (not setMinimumSize/resize) tells the window manager
        # this window is not meant to be tiled or maximized. Tiling
        # compositors (Hyprland, Sway, i3...) otherwise happily fullscreen
        # any "resizable" top-level window. We still change the size
        # ourselves at runtime via setFixedSize() again, which keeps it
        # floating instead of handing resize control to the WM.
        self.setFixedSize(width, height)

        self.build_ui()
        self.refresh_commands()

    def _build_flags(self, settings: dict):
        flags = Qt.FramelessWindowHint | Qt.Window
        if settings.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        return flags

    # --------------------------------------------------------
    # Liquid-glass painting
    # --------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, WINDOW_RADIUS, WINDOW_RADIUS)
        painter.setClipPath(path)

        settings = get_settings()
        opacity = int(settings.get("glass_opacity", 190))
        base_alpha = max(0, min(245, opacity))

        # base glass tint
        painter.fillRect(self.rect(), QColor(13, 15, 21, base_alpha))

        # diagonal liquid sheen (light source top-left, fading to a
        # faint dark pool bottom-right — the classic "liquid glass" look)
        sheen = QLinearGradient(0, 0, self.width(), self.height())
        sheen.setColorAt(0.0, QColor(255, 255, 255, 30))
        sheen.setColorAt(0.35, QColor(255, 255, 255, 8))
        sheen.setColorAt(0.65, QColor(255, 255, 255, 0))
        sheen.setColorAt(1.0, QColor(0, 0, 0, 45))
        painter.fillRect(self.rect(), sheen)

        # soft radial glow, top-left, like light bending through glass
        glow = QRadialGradient(
            self.width() * 0.2, self.height() * 0.1, self.width() * 0.6
        )
        glow.setColorAt(0.0, QColor(255, 255, 255, 45))
        glow.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(self.rect(), glow)

        # bright specular strip along the very top edge
        top_strip = QLinearGradient(0, 0, 0, min(120, self.height() * 0.3))
        top_strip.setColorAt(0.0, QColor(255, 255, 255, 55))
        top_strip.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(
            self.rect().adjusted(0, 0, 0, -int(self.height() * 0.7)), top_strip
        )

        painter.setClipping(False)

        # thin bright rim highlighting the glass edge
        rim = QPen(QColor(255, 255, 255, 85))
        rim.setWidth(1)
        painter.setPen(rim)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 18)
        root.setSpacing(10)

        header = QHBoxLayout()

        logo = QLabel("◈")
        logo_font = QFont()
        logo_font.setPointSize(17)
        logo.setFont(logo_font)
        logo.setStyleSheet("color: white;")
        header.addWidget(logo)

        title = QLabel("HUB")
        title_font = QFont()
        title_font.setPointSize(17)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
        title.setStyleSheet("color: white;")
        header.addWidget(title)

        header.addStretch()

        self.manage_button = GlassButton("✎")
        self.manage_button.setFixedSize(36, 34)
        self.settings_button = GlassButton("⚙")
        self.settings_button.setFixedSize(36, 34)
        close_button = GlassButton("×")
        close_button.setFixedSize(36, 34)

        header.addWidget(self.manage_button)
        header.addWidget(self.settings_button)
        header.addWidget(close_button)

        root.addLayout(header)

        self.manage_button.clicked.connect(self.toggle_manage)
        self.settings_button.clicked.connect(self.open_settings)
        # × hides Hub into the background — it keeps running so the
        # super+` toggle can bring it right back at the same position.
        # Ctrl+Q is the real "quit the process" shortcut.
        close_button.clicked.connect(self.hide)
        close_button.setToolTip("Hide (Hub keeps running — Ctrl+Q to quit)")

        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(QApplication.quit)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QWidget { background: transparent; }
        """)
        root.addWidget(self.scroll, 1)

        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(2, 3, 2, 3)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        self.scroll.setWidget(self.container)

    # --------------------------------------------------------
    # Commands (reflows column count to fit the current width)
    # --------------------------------------------------------

    def refresh_commands(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        config = load_config()
        commands = config.get("commands", {})
        settings = config.get("settings", {})

        card_size = int(settings.get("card_size", CARD_SIZE_DEFAULT))
        card_size = max(CARD_SIZE_MIN, min(CARD_SIZE_MAX, card_size))
        spacing = self.grid.horizontalSpacing() or 12

        viewport_width = self.scroll.viewport().width() if self.scroll.viewport().width() > 0 else self.width()
        columns = max(1, (viewport_width + spacing) // (card_size + spacing))

        row = 0
        col = 0

        for name, command in commands.items():
            card = CommandCard(name, command, self.manage_mode, self.container)
            card.clicked.connect(lambda n=name: self.run_command(n))
            card.edit_requested.connect(lambda n=name: self.edit_command(n))
            card.delete_requested.connect(lambda n=name: self.delete_command(n))

            self.grid.addWidget(card, row, col)

            col += 1
            if col >= columns:
                col = 0
                row += 1

        self.grid.setRowStretch(row + 1, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_commands()

    # --------------------------------------------------------
    # Execute  <<<--- ГЛАВНЫЙ ФИКС ЗДЕСЬ
    # --------------------------------------------------------

    def run_command(self, name):
        print(f"[HUB] clicked: {name}", flush=True)
        config = load_config()
        command = config.get("commands", {}).get(name)
        if not command:
            return

        for action in command.get("actions", []):
            monitor = (action.get("monitor") or "").strip()
            before = snapshot_windows() if monitor else None

            if monitor:
                focus_monitor(monitor)

            app_hint = None
            try:
                if action.get("type") == "browser":
                    browser = action.get("browser", "brave")
                    urls = action.get("urls") or []
                    parts = [browser, "--new-window", *urls]
                    app_hint = browser
                    print(f"[HUB] browser launch: {parts} → monitor={monitor or 'current'}", flush=True)
                    subprocess.Popen(parts, start_new_session=True)
                else:
                    raw = (action.get("command") or "").strip()
                    if not raw:
                        continue
                    try:
                        parts = shlex.split(raw)
                    except ValueError:
                        parts = [raw]
                    app_hint = parts[0] if parts else None
                    print(f"[HUB] app launch: {parts} → monitor={monitor or 'current'}", flush=True)
                    execute_action(action)
            except Exception as e:
                print(f"[HUB] ERROR: {e}", flush=True)
                import traceback
                traceback.print_exc()

            if monitor and before is not None:
                place_new_windows_on_monitor(
                    monitor, before, timeout=5.0, app_hint=app_hint
                )
                # Дать окну появиться, чтобы следующий action не перехватил его
                time.sleep(0.4)

        if get_settings().get("close_after_action", False):
            self.hide()

    # --------------------------------------------------------
    # Management
    # --------------------------------------------------------

    def toggle_manage(self):
        dialog = ManageWindow(self)
        dialog.changed.connect(self.refresh_commands)
        dialog.exec()

        self.manage_mode = False
        self.refresh_commands()

    def edit_command(self, name):
        config = load_config()
        command = config.get("commands", {}).get(name, {})
        editor = CommandEditor(name, command, self)
        editor.saved.connect(self.refresh_commands)
        editor.exec()

    def delete_command(self, name):
        result = QMessageBox.question(self, "Delete command", f"Delete '{name}'?")
        if result != QMessageBox.Yes:
            return

        config = load_config()
        command = config.get("commands", {}).get(name, {})
        remove_old_icon(command.get("icon"))
        config.get("commands", {}).pop(name, None)
        save_config(config)
        self.refresh_commands()

    # --------------------------------------------------------
    # Settings
    # --------------------------------------------------------

    def open_settings(self):
        dialog = SettingsWindow(self)
        dialog.settings_saved.connect(self.apply_settings)
        dialog.exec()

    def apply_settings(self):
        settings = get_settings()

        self.setWindowFlags(self._build_flags(settings))
        self.show()

        width = int(settings.get("window_width", WINDOW_DEFAULT_WIDTH))
        height = int(settings.get("window_height", WINDOW_DEFAULT_HEIGHT))
        width = max(WINDOW_MIN_WIDTH, min(1000, width))
        height = max(WINDOW_MIN_HEIGHT, min(1000, height))

        if (width, height) != (self.width(), self.height()):
            self.setFixedSize(width, height)
            if settings.get("center_window", True):
                screen = QApplication.primaryScreen().availableGeometry()
                self.move(screen.center() - self.rect().center())

        self.refresh_commands()
        self.update()

    # --------------------------------------------------------
    # Dragging + edge resizing (frameless window has no native grips)
    # --------------------------------------------------------

    def _edges_at(self, pos):
        m = self.RESIZE_MARGIN
        rect = self.rect()
        return {
            "left": pos.x() <= m,
            "right": pos.x() >= rect.width() - m,
            "top": pos.y() <= m,
            "bottom": pos.y() >= rect.height() - m,
        }

    def _cursor_for_edges(self, edges):
        l, r, t, b = edges["left"], edges["right"], edges["top"], edges["bottom"]
        if (l and t) or (r and b):
            return Qt.SizeFDiagCursor
        if (r and t) or (l and b):
            return Qt.SizeBDiagCursor
        if l or r:
            return Qt.SizeHorCursor
        if t or b:
            return Qt.SizeVerCursor
        return Qt.ArrowCursor

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            edges = self._edges_at(pos)

            if any(edges.values()):
                self.resize_edges = edges
                self.resize_start_geo = self.geometry()
                self.resize_start_pos = event.globalPosition().toPoint()
            else:
                child = self.childAt(pos)
                if child is None:
                    self.drag_position = (
                        event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    )

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resize_edges and event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self.resize_start_pos
            geo = self.resize_start_geo
            x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()

            if self.resize_edges["left"]:
                new_w = max(WINDOW_MIN_WIDTH, min(1000, w - delta.x()))
                x = x + (w - new_w)
                w = new_w
            elif self.resize_edges["right"]:
                w = max(WINDOW_MIN_WIDTH, min(1000, w + delta.x()))

            if self.resize_edges["top"]:
                new_h = max(WINDOW_MIN_HEIGHT, min(1000, h - delta.y()))
                y = y + (h - new_h)
                h = new_h
            elif self.resize_edges["bottom"]:
                h = max(WINDOW_MIN_HEIGHT, min(1000, h + delta.y()))

            self.setFixedSize(w, h)
            self.move(x, y)

        elif self.drag_position and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)

        elif not event.buttons():
            edges = self._edges_at(event.position().toPoint())
            self.setCursor(self._cursor_for_edges(edges))

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.resize_edges:
            save_settings_patch({
                "window_width": self.width(),
                "window_height": self.height(),
            })
        self.resize_edges = None
        self.drag_position = None
        super().mouseReleaseEvent(event)


# ============================================================
# Application
# ============================================================

HUB_IPC_SERVER_NAME = "hub-ipc"


def _toggle_running_instance() -> bool:
    """
    Tries to reach an already-running Hub via local IPC and tells it to
    toggle its visibility. Returns True if one was found (meaning this
    process should just exit — the running instance handled it).
    """
    client = QLocalSocket()
    client.connectToServer(HUB_IPC_SERVER_NAME)
    if client.waitForConnected(150):
        client.write(b"toggle")
        client.waitForBytesWritten(150)
        client.disconnectFromServer()
        return True
    return False


def main():
    ensure_dirs()
    ensure_desktop_entry()

    app = QApplication(sys.argv)
    app.setDesktopFileName("hub")
    app.setApplicationName("Hub")
    app.setApplicationDisplayName("Hub")
    app.setStyle("Fusion")
    apply_dark_palette(app)

    font = QFont("Inter", 10)
    app.setFont(font)

    # The exact same command (super+space app launcher entry, a terminal,
    # or a super+` hotkey) either starts Hub, or — if it's already
    # running in the background — just shows/hides it right where it
    # was, instead of launching a second instance.
    if _toggle_running_instance():
        return 0

    app.setQuitOnLastWindowClosed(False)

    QLocalServer.removeServer(HUB_IPC_SERVER_NAME)
    ipc_server = QLocalServer()
    ipc_server.listen(HUB_IPC_SERVER_NAME)

    window = HubWindow()

    def handle_ipc_connection():
        client = ipc_server.nextPendingConnection()
        if not client:
            return
        client.waitForReadyRead(150)
        message = bytes(client.readAll())
        if message == b"toggle":
            if window.isVisible():
                window.hide()
            else:
                window.show()
                window.raise_()
                window.activateWindow()
        client.disconnectFromServer()

    ipc_server.newConnection.connect(handle_ipc_connection)

    settings = get_settings()

    if settings.get("center_window", True):
        screen = app.primaryScreen().availableGeometry()
        window.move(screen.center() - window.rect().center())

    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
