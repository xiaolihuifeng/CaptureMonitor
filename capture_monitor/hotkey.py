"""Windows global hotkey binding (PyQt5 native event filter).

Registers a system-wide hotkey through ``RegisterHotKey`` against a hidden
``QWidget``'s real HWND, so WM_HOTKEY arrives as a window message that Qt
routes through ``QAbstractNativeEventFilter`` reliably. Emits ``activated``
when the hotkey is pressed, even while the application is not focused.
On non-Windows platforms every operation degrades to a no-op so the module
stays importable and the application remains runnable headless.
"""

from __future__ import annotations

import ctypes
import logging
import sys

from PyQt5.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget

from capture_monitor.keys import MOD_NOREPEAT, parse_hotkey

WM_HOTKEY = 0x0312
_HOTKEY_ID = 0xB0B0
_IS_WINDOWS = sys.platform == "win32"

logger = logging.getLogger("capture_monitor.hotkey")


class GlobalHotkey(QObject, QAbstractNativeEventFilter):
    """A single system-wide hotkey bound to one activation signal."""

    activated = pyqtSignal()

    def __init__(self, spec: str = "F9", parent=None) -> None:
        super().__init__(parent)
        self._spec = spec
        self._registered = False
        self._window: QWidget | None = None
        self._hwnd: int | None = None

    @property
    def enabled(self) -> bool:
        return self._registered

    @property
    def spec(self) -> str:
        return self._spec

    def _ensure_window(self) -> bool:
        """Lazily create a hidden QWidget and cache its real HWND."""
        if self._window is not None:
            return True
        if not _IS_WINDOWS or QCoreApplication.instance() is None:
            return False
        self._window = QWidget()  # never shown; only used for its HWND
        self._hwnd = int(self._window.winId())
        return True

    def register(self) -> bool:
        """Register the hotkey with Windows; no-op failure elsewhere."""
        if self._registered:
            return True
        parsed = parse_hotkey(self._spec)
        if parsed is None or not _IS_WINDOWS:
            logger.warning("无法注册全局热键: spec=%r (仅支持 Windows)", self._spec)
            return False
        if not self._ensure_window():
            logger.warning("无法注册全局热键: spec=%r (缺少 QApplication)", self._spec)
            return False
        modifiers, vk = parsed
        ok = bool(
            ctypes.windll.user32.RegisterHotKey(
                self._hwnd, _HOTKEY_ID, modifiers | MOD_NOREPEAT, vk
            )
        )
        if not ok:
            err = ctypes.windll.kernel32.GetLastError()
            logger.warning("RegisterHotKey 失败 spec=%r err=%s (可能被占用)", self._spec, err)
            return False
        app = QCoreApplication.instance()
        if app is not None:
            app.installNativeEventFilter(self)
        self._registered = True
        logger.info("全局热键已注册: %s (hwnd=%s)", self._spec, self._hwnd)
        return True

    def unregister(self) -> None:
        """Unregister the hotkey if registered; guard against double calls."""
        if not self._registered:
            return
        if _IS_WINDOWS:
            ctypes.windll.user32.UnregisterHotKey(self._hwnd, _HOTKEY_ID)
        app = QCoreApplication.instance()
        if app is not None:
            app.removeNativeEventFilter(self)
        self._registered = False
        logger.info("全局热键已注销: %s", self._spec)

    def set_spec(self, spec: str) -> bool:
        """Change the hotkey spec, re-registering if it was enabled."""
        was_enabled = self._registered
        self.unregister()
        self._spec = spec
        if was_enabled:
            return self.register()
        return False

    def set_enabled(self, on: bool) -> bool:
        """Enable (register) or disable (unregister) the hotkey."""
        if on:
            return self.register()
        self.unregister()
        return False

    def nativeEventFilter(self, eventType, message):
        """Emit ``activated`` on WM_HOTKEY with our registration id."""
        if not _IS_WINDOWS:
            return False, 0
        try:
            et = bytes(eventType)
        except Exception:
            return False, 0
        if et in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == _HOTKEY_ID:
                logger.info("热键触发: %s", self._spec)
                self.activated.emit()
        return False, 0
