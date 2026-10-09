"""Filesystem location helpers.

All paths resolve relative to the program directory: the project root in
development, or the folder containing the frozen executable when packaged.
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def program_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", program_dir()))
    return program_dir()


def default_image_dir() -> Path:
    return program_dir() / "Image"


def config_path() -> Path:
    return program_dir() / "config.json"


def log_path() -> Path:
    return program_dir() / "CaptureMonitor.log"


def resolve_reference(name: str) -> Path:
    candidate = Path(name)
    if candidate.is_absolute():
        return candidate
    for base in (program_dir(), resource_dir()):
        resolved = base / candidate
        if resolved.exists():
            return resolved
    return program_dir() / candidate
