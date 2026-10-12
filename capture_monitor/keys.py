"""Global hotkey spec parsing (pure Python, no PyQt).

Translates human-readable hotkey strings like ``"F9"`` or ``"Ctrl+Alt+S"``
into ``(modifiers, virtual-key)`` tuples understood by the Win32
``RegisterHotKey`` API. Importable and testable headless.
"""

from __future__ import annotations

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

_MODIFIERS = {
    "CTRL": MOD_CONTROL,
    "CONTROL": MOD_CONTROL,
    "ALT": MOD_ALT,
    "SHIFT": MOD_SHIFT,
    "WIN": MOD_WIN,
    "META": MOD_WIN,
}

_KEY_TO_VK: dict[str, int] = {
    "ESC": 0x1B,
    "TAB": 0x09,
    "SPACE": 0x20,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
    "HOME": 0x24,
    "END": 0x23,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "UP": 0x26,
    "DOWN": 0x28,
    "LEFT": 0x25,
    "RIGHT": 0x27,
    "PRINTSCREEN": 0x2C,
}
_KEY_TO_VK.update({f"F{i}": 0x6F + i for i in range(1, 25)})
_KEY_TO_VK.update({chr(ord("A") + i): ord("A") + i for i in range(26)})
_KEY_TO_VK.update({str(i): ord("0") + i for i in range(10)})


def parse_hotkey(spec: str) -> tuple[int, int] | None:
    """Parse 'F9' / 'Ctrl+Alt+S' / 'shift + 1' -> (modifiers, vk).

    Case-insensitive, spaces allowed. Returns None if invalid/empty.
    Modifiers accepted: ctrl/control, alt, shift, win/meta.
    Last non-modifier token is the key. Unknown keys -> None.
    """
    if not spec:
        return None
    modifiers = 0
    vk: int | None = None
    for token in spec.split("+"):
        token = token.strip()
        if not token:
            return None
        upper = token.upper()
        modifier = _MODIFIERS.get(upper)
        if modifier is not None:
            modifiers |= modifier
            continue
        vk = _KEY_TO_VK.get(upper)
        if vk is None:
            return None
    if vk is None:
        return None
    return modifiers, vk
