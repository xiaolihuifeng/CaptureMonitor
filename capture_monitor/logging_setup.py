"""Root logging setup (stdlib only, no PyQt).

Installs a rotating file handler for ``CaptureMonitor.log`` plus a stderr
handler when a console exists (a windowed EXE has ``sys.stderr = None``).
Repeated calls never add duplicate handlers for the same target, and any
filesystem failure degrades to console-only logging instead of crashing.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from capture_monitor import paths

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(path: str | Path | None = None, level: int = logging.INFO) -> str:
    """Configure root logging and return the log file path as a string.

    Never raises: if the target directory cannot be created or the file
    cannot be opened, logging continues without a file handler.
    """
    target = Path(path) if path else paths.log_path()
    root = logging.getLogger()
    root.setLevel(level)
    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        resolved = target.resolve()
        if not any(
            isinstance(handler, RotatingFileHandler)
            and Path(handler.baseFilename or "").resolve() == resolved
            for handler in root.handlers
        ):
            file_handler = RotatingFileHandler(
                target, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
    except OSError:
        pass
    if sys.stderr is not None and not any(
        isinstance(handler, logging.StreamHandler)
        and getattr(handler, "stream", None) is sys.stderr
        for handler in root.handlers
    ):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)
    return str(target)
