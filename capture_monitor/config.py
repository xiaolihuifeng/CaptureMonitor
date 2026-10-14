"""Tolerant JSON-backed configuration.

Stdlib only: a dataclass schema plus plain ``json`` persistence. Unknown keys
are ignored on load; corrupt files fall back to defaults without crashing.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from capture_monitor import paths


@dataclass
class Config:
    reference_image: str = "DEMO.png"
    save_dir: str = ""                     # empty string => default_image_dir()
    match_threshold: float = 0.80
    match_region: list | None = None       # [x, y, w, h]; None => whole frame
    capture_interval_ms: int = 1000
    min_confirm_frames: int = 2
    dedup_hamming_threshold: int = 4       # 0..64
    dedup_max_diff: float = 0.008           # 0..1 mean-abs grayscale diff; combined with hash => duplicate
    monitor_index: int = 0
    image_format: str = "png"              # "png" or "jpg"
    auto_start_monitor: bool = True
    hotkey: str = "F9"
    hotkey_enabled: bool = True
    debug_keys: bool = False                # 记录按键调试信息(排查快捷键)

    def resolved_save_dir(self) -> Path:
        if self.save_dir:
            return Path(self.save_dir)
        return paths.default_image_dir()

    def resolved_reference(self) -> Path:
        return paths.resolve_reference(self.reference_image)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        config = cls()
        known = cls.__dataclass_fields__
        for key, value in d.items():
            if key in known:
                setattr(config, key, value)
        return config

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        target = Path(path) if path is not None else paths.config_path()
        if not target.exists():
            config = cls()
            config.save(target)
            return config
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return cls()
        if not isinstance(data, dict):
            return cls()
        return cls.from_dict(data)

    def save(self, path: Path | None = None) -> None:
        target = Path(path) if path is not None else paths.config_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2, ensure_ascii=False)
