"""Windows global hotkey via a low-level keyboard hook (PyQt5).

Uses ``SetWindowsHookEx(WH_KEYBOARD_LL)`` so the configured key is detected
system-wide regardless of focus or ``RegisterHotKey`` message-routing quirks.
The hook callback never does heavy work inline (it only emits a queued Qt
signal), so Windows never silently times the hook out. On non-Windows every
operation degrades to a no-op so the module stays importable headless.
"""

from __future__ import annotations

import ctypes
import logging
import sys

from PyQt5.QtCore import QObject, pyqtSignal

from capture_monitor.keys import MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, parse_hotkey

logger = logging.getLogger("capture_monitor.hotkey")

_IS_WINDOWS = sys.platform == "win32"

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104

_VK_CONTROL = 0x11
_VK_MENU = 0x12  # Alt
_VK_SHIFT = 0x10
_VK_LWIN = 0x5B
_VK_RWIN = 0x5C

if _IS_WINDOWS:
    from ctypes import wintypes

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("vkCode", wintypes.DWORD),
            ("scanCode", wintypes.DWORD),
            ("flags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_size_t),
        ]

    _LRESULT = ctypes.c_ssize_t
    _HOOKPROC = ctypes.WINFUNCTYPE(_LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _user32.SetWindowsHookExW.restype = wintypes.HHOOK
    _user32.SetWindowsHookExW.argtypes = [
        ctypes.c_int, _HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD
    ]
    _user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    _user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
    _user32.CallNextHookEx.restype = _LRESULT
    _user32.CallNextHookEx.argtypes = [
        wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
    ]
    _user32.GetAsyncKeyState.restype = ctypes.c_uint16
    _user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
else:  # pragma: no cover - non-Windows import path
    _LRESULT = ctypes.c_ssize_t
    _HOOKPROC = None


class GlobalHotkey(QObject):
    """A single system-wide hotkey bound to one activation signal."""

    activated = pyqtSignal()

    def __init__(self, spec: str = "F9", parent=None) -> None:
        super().__init__(parent)
        self._spec = spec
        self._registered = False
        self._hook = None
        self._proc = None
        self._vk = 0
        self._mods = 0

    @property
    def enabled(self) -> bool:
        return self._registered

    @property
    def spec(self) -> str:
        return self._spec

    def register(self) -> bool:
        """Install the low-level keyboard hook; no-op failure off Windows."""
        if self._registered:
            return True
        parsed = parse_hotkey(self._spec)
        if parsed is None:
            logger.warning("无法启用全局热键: spec=%r 解析失败", self._spec)
            return False
        if not _IS_WINDOWS:
            logger.warning("无法启用全局热键: spec=%r (仅支持 Windows)", self._spec)
            return False
        self._mods, self._vk = parsed
        try:
            self._proc = _HOOKPROC(self._on_key)
            self._hook = _user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, None, 0)
        except Exception:
            logger.exception("安装键盘钩子异常: spec=%r", self._spec)
            self._proc = None
            self._hook = None
            return False
        if not self._hook:
            logger.warning("SetWindowsHookEx 失败 err=%s", ctypes.get_last_error())
            return False
        self._registered = True
        logger.info("全局热键已启用(键盘钩子): %s", self._spec)
        return True

    def unregister(self) -> None:
        """Remove the keyboard hook if installed; guard against double calls."""
        if not self._registered:
            return
        if _IS_WINDOWS and self._hook:
            try:
                _user32.UnhookWindowsHookEx(self._hook)
            except Exception:
                logger.exception("卸载键盘钩子异常")
        self._hook = None
        self._proc = None
        self._registered = False
        logger.info("全局热键已停用: %s", self._spec)

    def set_spec(self, spec: str) -> bool:
        """Change the hotkey spec, re-registering if it was enabled."""
        was_enabled = self._registered
        self.unregister()
        self._spec = spec
        if was_enabled:
            return self.register()
        return False

    def set_enabled(self, on: bool) -> bool:
        """Enable (install hook) or disable (remove hook) the hotkey."""
        if on:
            return self.register()
        self.unregister()
        return False

    def _modifiers_down(self) -> int:
        state = 0
        if _user32.GetAsyncKeyState(_VK_CONTROL) & 0x8000:
            state |= MOD_CONTROL
        if _user32.GetAsyncKeyState(_VK_MENU) & 0x8000:
            state |= MOD_ALT
        if _user32.GetAsyncKeyState(_VK_SHIFT) & 0x8000:
            state |= MOD_SHIFT
        if (_user32.GetAsyncKeyState(_VK_LWIN) | _user32.GetAsyncKeyState(_VK_RWIN)) & 0x8000:
            state |= MOD_WIN
        return state

    def _on_key(self, n_code, w_param, l_param):
        if n_code == 0 and w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
            kb = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if kb.vkCode == self._vk and self._modifiers_down() == self._mods:
                # Emit only (queued by the caller) — keep the hook fast.
                self.activated.emit()
        return _user32.CallNextHookEx(None, n_code, w_param, l_param)
