"""Qt-free capture decision engine.

Pure logic: scores frames against the interface detector, waits for
``min_confirm_frames`` consecutive matches, deduplicates via dHash and saves
frames to the configured directory. No PyQt imports - safe to import and
test in a headless environment.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from capture_monitor.comparer import ImageComparer
from capture_monitor.config import Config

REASON_SAVED = "saved"
REASON_DUPLICATE = "duplicate"
REASON_PENDING = "pending"
REASON_NO_INTERFACE = "no_interface"
REASON_MANUAL = "manual"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}


@dataclass
class CaptureResult:
    timestamp: float
    saved: bool
    path: str | None
    score: float
    reason: str


class MonitorEngine:
    def __init__(self, config: Config, detector, comparer: ImageComparer | None = None,
                 on_captured=None) -> None:
        self.config = config
        self.detector = detector
        self.comparer = comparer if comparer is not None else ImageComparer(
            config.dedup_hamming_threshold, getattr(config, "dedup_max_diff", 0.008)
        )
        self.on_captured = on_captured
        self._confirm = 0
        self._last_hash: int | None = None
        self._last_signature: np.ndarray | None = None
        self._history: list[dict] = []

    def tick(self, frame_bgr: np.ndarray) -> CaptureResult:
        score = self.detector.score(frame_bgr)
        if score < self.config.match_threshold:
            self._confirm = 0
            return CaptureResult(time.time(), False, None, score, REASON_NO_INTERFACE)
        self._confirm += 1
        if self._confirm < self.config.min_confirm_frames:
            return CaptureResult(time.time(), False, None, score, REASON_PENDING)
        current_hash = self.comparer.hash(frame_bgr)
        current_signature = self.comparer.signature(frame_bgr)
        if self._last_hash is not None and self._last_signature is not None:
            same_layout = self.comparer.is_duplicate(self._last_hash, current_hash)
            same_pixels = (
                self.comparer.difference(self._last_signature, current_signature)
                <= self.comparer.max_diff
            )
            if same_layout and same_pixels:
                return CaptureResult(time.time(), False, None, score, REASON_DUPLICATE)
        timestamp = time.time()
        path = self._save_frame(frame_bgr, score)
        self._last_hash = current_hash
        self._last_signature = current_signature
        entry = {"path": path, "time": timestamp, "score": score, "name": Path(path).name}
        self._history.append(entry)
        if self.on_captured is not None:
            self.on_captured(path, dict(entry))
        return CaptureResult(timestamp, True, path, score, REASON_SAVED)

    def capture_now(self, frame_bgr: np.ndarray) -> CaptureResult:
        """Force-save the current frame regardless of match or dedup state."""
        score = self.detector.score(frame_bgr)
        timestamp = time.time()
        path = self._save_frame(frame_bgr, score)
        entry = {"path": path, "time": timestamp, "score": score, "name": Path(path).name}
        self._history.append(entry)
        self._last_hash = self.comparer.hash(frame_bgr)
        self._last_signature = self.comparer.signature(frame_bgr)
        if self.on_captured is not None:
            self.on_captured(path, dict(entry))
        return CaptureResult(timestamp, True, path, score, REASON_MANUAL)

    def _save_frame(self, frame_bgr: np.ndarray, score: float) -> str:
        directory = self.config.resolved_save_dir()
        directory.mkdir(parents=True, exist_ok=True)
        image_format = str(self.config.image_format).lower()
        ext = "jpg" if image_format in ("jpg", "jpeg") else "png"
        now = datetime.now()
        stem = "cap_%s_%03d" % (now.strftime("%Y%m%d_%H%M%S"), now.microsecond // 1000)
        target = directory / f"{stem}.{ext}"
        counter = 1
        while target.exists():
            target = directory / f"{stem}_{counter}.{ext}"
            counter += 1
        params = [cv2.IMWRITE_JPEG_QUALITY, 95] if ext == "jpg" else []
        ok = cv2.imwrite(str(target), frame_bgr, params)
        if not ok:
            raise IOError(f"Failed to write image: {target}")
        return str(target)

    @property
    def captured(self) -> list[dict]:
        return list(self._history)

    def scan_existing(self) -> list[dict]:
        directory = self.config.resolved_save_dir()
        files: list[tuple[float, Path]] = []
        if directory.is_dir():
            for candidate in directory.iterdir():
                try:
                    if not candidate.is_file() or candidate.suffix.lower() not in IMAGE_EXTS:
                        continue
                    files.append((candidate.stat().st_mtime, candidate))
                except OSError:
                    continue
        files.sort(key=lambda item: item[0], reverse=True)
        entries = [
            {"path": str(path), "time": mtime, "score": None, "name": path.name}
            for mtime, path in files
        ]
        if not self._history:
            self._history = list(entries)
        if entries:
            try:
                image = cv2.imread(entries[0]["path"], cv2.IMREAD_COLOR)
                if image is not None:
                    self._last_hash = self.comparer.hash(image)
                    self._last_signature = self.comparer.signature(image)
            except Exception:
                pass
        return entries

    def reset(self) -> None:
        self._confirm = 0
        self._last_hash = None
        self._last_signature = None
