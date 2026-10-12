"""PyQt5 application assembly: tray + list window + engine wiring."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QSharedMemory
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from capture_monitor import paths
from capture_monitor.capture import ScreenCapturer
from capture_monitor.config import Config
from capture_monitor.detector import InterfaceDetector
from capture_monitor.engine import MonitorEngine
from capture_monitor.hotkey import GlobalHotkey
from capture_monitor.list_window import CaptureListWindow
from capture_monitor.tray import TrayController


def _icon() -> QIcon:
    for base in (paths.program_dir(), paths.resource_dir()):
        candidate = base / "assets" / "icon.png"
        if candidate.exists():
            return QIcon(str(candidate))
    return QIcon()


def _build_detector(config: Config):
    reference = config.resolved_reference()
    if not reference.exists():
        return None
    region = tuple(config.match_region) if config.match_region else None
    return InterfaceDetector.from_file(reference, region)


def main(argv=None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("CaptureMonitor")
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(_icon())

    shared_memory = QSharedMemory("CaptureMonitorSingleInstance")
    if not shared_memory.create(1):
        QMessageBox.warning(None, "CaptureMonitor", "CaptureMonitor 已在运行")
        return 1

    config = Config.load()
    detector = _build_detector(config)
    if detector is None:
        QMessageBox.warning(
            None, "CaptureMonitor", f"参考图不存在: {config.resolved_reference()}"
        )
        return 2

    engine = MonitorEngine(config, detector)
    engine.scan_existing()
    capturer = ScreenCapturer(config.monitor_index)
    window = CaptureListWindow(config)
    tray = TrayController(app, config, engine, capturer, window, icon_path=None)

    def reload_config(new_config: Config) -> None:
        new_detector = _build_detector(new_config)
        if new_detector is None:
            return
        engine.config = new_config
        engine.detector = new_detector
        tray.apply_config(new_config)
        hotkey.set_spec(new_config.hotkey)
        hotkey.set_enabled(new_config.hotkey_enabled)

    window.on_config_changed = reload_config
    tray.start()
    window.refresh()
    hotkey = GlobalHotkey(config.hotkey)
    if config.hotkey_enabled:
        hotkey.register()
    hotkey.activated.connect(tray.manual_capture)
    app.aboutToQuit.connect(hotkey.unregister)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("warning: system tray is not available", file=sys.stderr)
    return app.exec_()
