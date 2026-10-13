"""PyQt5 application assembly: tray + list window + engine wiring."""

from __future__ import annotations

import logging
import sys

from PyQt5.QtCore import QSharedMemory
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from capture_monitor import __version__, paths
from capture_monitor.capture import ScreenCapturer
from capture_monitor.config import Config
from capture_monitor.detector import InterfaceDetector
from capture_monitor.engine import MonitorEngine
from capture_monitor.hotkey import GlobalHotkey
from capture_monitor.list_window import CaptureListWindow
from capture_monitor.logging_setup import setup_logging
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
    log_file = setup_logging()
    logger = logging.getLogger("capture_monitor.app")

    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("CaptureMonitor")
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(_icon())

    shared_memory = QSharedMemory("CaptureMonitorSingleInstance")
    if not shared_memory.create(1):
        QMessageBox.warning(None, "CaptureMonitor", "CaptureMonitor 已在运行")
        return 1

    config = Config.load()
    logger.info("CaptureMonitor v%s 启动; 日志=%s", __version__, log_file)
    logger.info(
        "配置: save_dir=%s reference_image=%s match_threshold=%s min_confirm_frames=%s "
        "dedup_max_diff=%s hotkey=%s hotkey_enabled=%s",
        config.resolved_save_dir(),
        config.reference_image,
        config.match_threshold,
        config.min_confirm_frames,
        config.dedup_max_diff,
        config.hotkey,
        config.hotkey_enabled,
    )
    reference = config.resolved_reference()
    logger.info("参考图: %s 存在=%s", reference, reference.exists())
    detector = _build_detector(config)
    if detector is None:
        QMessageBox.warning(
            None, "CaptureMonitor", f"参考图不存在: {config.resolved_reference()}"
        )
        return 2

    engine = MonitorEngine(config, detector)
    engine.scan_existing()
    capturer = ScreenCapturer(config.monitor_index)
    hotkey = GlobalHotkey(config.hotkey)
    tray = TrayController(app, config, engine, capturer, None, icon_path=None)

    def reload_config(new_config: Config) -> None:
        new_detector = _build_detector(new_config)
        if new_detector is None:
            logger.warning("重新加载配置失败: 参考图不存在 %s", new_config.resolved_reference())
            return
        engine.config = new_config
        engine.detector = new_detector
        tray.apply_config(new_config)
        hotkey.set_spec(new_config.hotkey)
        if new_config.hotkey_enabled:
            if hotkey.set_enabled(True):
                logger.info("全局热键已更新: %s", new_config.hotkey)
            else:
                logger.warning("全局快捷键注册失败: %s", new_config.hotkey)
                tray.notify("快捷键注册失败", "快捷键可能被其他程序占用，请在设置里更换")
        else:
            hotkey.set_enabled(False)
            logger.info("全局快捷键已禁用")

    window = CaptureListWindow(
        config, on_config_changed=reload_config, on_manual_capture=tray.manual_capture
    )
    tray.list_window = window

    tray.start()
    window.refresh()
    if config.hotkey_enabled:
        if not hotkey.register():
            logger.warning("全局快捷键注册失败: %s", config.hotkey)
            tray.notify("快捷键注册失败", "F9 可能被其他程序占用，请在设置里更换")
    else:
        logger.info("全局快捷键已禁用")
    hotkey.activated.connect(tray.manual_capture)
    app.aboutToQuit.connect(hotkey.unregister)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        logger.warning("系统托盘不可用")
    return app.exec_()
