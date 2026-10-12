"""Tests for capture_monitor.keys (pure parsing, no PyQt imports)."""

from __future__ import annotations

from capture_monitor.keys import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
    MOD_WIN,
    parse_hotkey,
)


def test_parse_hotkey_valid_specs():
    assert parse_hotkey("F9") == (0, 0x78)
    assert parse_hotkey(" f9 ") == (0, 0x78)
    assert parse_hotkey("Ctrl+Alt+S") == (MOD_CONTROL | MOD_ALT, 0x53)
    assert parse_hotkey("Shift+1") == (MOD_SHIFT, 0x31)
    assert parse_hotkey("control + shift + win + F12") == (
        MOD_CONTROL | MOD_SHIFT | MOD_WIN,
        0x7B,
    )
    assert parse_hotkey("Meta+PrintScreen") == (MOD_WIN, 0x2C)
    assert parse_hotkey("Esc") == (0, 0x1B)


def test_parse_hotkey_invalid_returns_none():
    assert parse_hotkey("Bogus") is None
    assert parse_hotkey("") is None
    assert parse_hotkey("Ctrl+") is None
