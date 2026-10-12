"""Windows global hotkey binding (PyQt5 native event filter).

Registers a system-wide hotkey through ``RegisterHotKey`` and emits
``activated`` when it is pressed, even while the application is not focused.
On non-Windows platforms every operation degrades to a no-op so the module
stays importable and the application remains runnable headless.
"""

from __future__ import annotations

import ctypes
import sys

from PyQt5.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, pyqtSignal

from capture_monitor.keys import MOD_NOREPEAT, parse_hotkey

WM_HOTKEY = 0x0312
_HOTKEY_ID = 0xB0B0
_IS_WINDOWS = sys.platform == "win32"


class GlobalHotkey(QObject, QAbstractNativeEventFilter):
    """A single system-wide hotkey bound to one activation signal."""

    activated = pyqtSignal()

    def __init__(self, spec: str = "F9", parent=None) -> None:
        super().__init__(parent)
        self._spec = spec
        self._registered = False

    @property
    def enabled(self) -> bool:
        return self._registered

    @property
    def spec(self) -> str:
        return self._spec

    def register(self) -> bool:
        """Register the hotkey with Windows; no-op failure elsewhere."""
        if self._registered:
            return True
        parsed = parse_hotkey(self._spec)
        if parsed is None or not _IS_WINDOWS:
            return False
        modifiers, vk = parsed
        if not ctypes.windll.user32.RegisterHotKey(
            None, _HOTKEY_ID, modifiers | MOD_NOREPEAT, vk
        ):
            return False
        self._registered = True
        app = QCoreApplication.instance()
        if app is not None:
            app.installNativeEventFilter(self)
        return True

    def unregister(self) -> None:
        """Unregister the hotkey if registered; guard against double calls."""
        if not self._registered:
            return
        if _IS_WINDOWS:
            ctypes.windll.user32.UnregisterHotKey(None, _HOTKEY_ID)
        app = QCoreApplication.instance()
        if app is not None:
            app.removeNativeEventFilter(self)
        self._registered = False

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
        if _IS_WINDOWS and eventType in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == _HOTKEY_ID:
                self.activated.emit()
        return False, 0
