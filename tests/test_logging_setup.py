"""Tests for capture_monitor.logging_setup (stdlib only, no PyQt)."""

from __future__ import annotations

import logging
from pathlib import Path

from capture_monitor.logging_setup import setup_logging


def test_setup_logging_writes_records_to_file(tmp_path):
    path = setup_logging(tmp_path / "sub" / "t.log")
    logging.getLogger("capture_monitor.test").info("hello")
    target = Path(path)
    assert target.exists()
    assert "hello" in target.read_text(encoding="utf-8")


def test_setup_logging_twice_does_not_raise(tmp_path):
    first = setup_logging(tmp_path / "t.log")
    second = setup_logging(tmp_path / "t.log")
    assert second == first


def test_setup_logging_bad_paths_do_not_raise(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    assert setup_logging(blocker / "x.log")  # parent is a file, not a directory
    assert setup_logging("/proc/nonexist/x.log")  # directory cannot be created
