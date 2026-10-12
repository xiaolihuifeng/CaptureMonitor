"""System tray controller (PyQt5)."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QObject, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMenu, QSystemTrayIcon


class TrayController(QObject):
    def __init__(self, app, config, engine, capturer, list_window, icon_path=None,
                 parent=None) -> None:
        super().__init__(parent)
        self.app = app
        self.config = config
        self.engine = engine
        self.capturer = capturer
        self.list_window = list_window
        self._icon_path = icon_path
        self._tray: QSystemTrayIcon | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        if self._icon_path and Path(self._icon_path).exists():
            icon = QIcon(self._icon_path)
        else:
            icon = QApplication.windowIcon()
        self._tray = QSystemTrayIcon(icon, self)
        menu = QMenu()
        open_action = menu.addAction("采图列表")
        open_action.triggered.connect(self._open_list)
        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(self._quit)
        self._tray.setContextMenu(menu)
        self._tray.setToolTip(
            f"CaptureMonitor 采图监控 (快捷键 {getattr(self.config, 'hotkey', 'F9')})"
        )
        self._tray.show()
        self._timer.setInterval(max(1, int(self.config.capture_interval_ms)))
        if self.config.auto_start_monitor:
            self._timer.start()

    def _tick(self) -> None:
        frame = self.capturer.grab()
        if frame is None:
            return
        result = self.engine.tick(frame)
        if result.saved and self.list_window is not None:
            self.list_window.add_capture(
                result.path, {"time": result.timestamp, "score": result.score}
            )

    def manual_capture(self) -> None:
        frame = self.capturer.grab()
        if frame is None:
            return
        result = self.engine.capture_now(frame)
        if result.saved:
            if self.list_window is not None:
                self.list_window.add_capture(
                    result.path, {"time": result.timestamp, "score": result.score}
                )
            if self._tray is not None:
                self._tray.showMessage(
                    "CaptureMonitor",
                    f"已采图：{Path(result.path).name}",
                    QSystemTrayIcon.Information,
                    2000,
                )

    def _open_list(self) -> None:
        if self.list_window is None:
            return
        self.list_window.refresh()
        self.list_window.show()
        self.list_window.raise_()
        self.list_window.activateWindow()

    def _quit(self) -> None:
        self.stop()
        if self._tray is not None:
            self._tray.hide()
        self.app.quit()

    def apply_config(self, config) -> None:
        self.config = config
        self._timer.setInterval(max(1, int(config.capture_interval_ms)))
        if config.auto_start_monitor:
            self._timer.start()
        else:
            self._timer.stop()

    def stop(self) -> None:
        self._timer.stop()
