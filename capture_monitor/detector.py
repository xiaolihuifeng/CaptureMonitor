"""Interface-presence detection via normalized template matching.

Frames are canonicalized to a fixed small size before matching so scores are
invariant to capture resolution. numpy + cv2 only.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def _to_uint8(image: np.ndarray) -> np.ndarray:
    if image.dtype == np.uint8:
        return image
    if image.dtype.kind == "f":
        image = image.astype(np.float32)
        if float(image.max()) <= 1.0 and float(image.min()) >= 0.0:
            image = image * 255.0
    return np.clip(image, 0, 255).astype(np.uint8)


def _to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _crop_region(frame: np.ndarray, region: tuple) -> np.ndarray:
    x, y, width, height = region
    frame_height, frame_width = frame.shape[:2]
    x0 = max(0, int(x))
    y0 = max(0, int(y))
    x1 = min(frame_width, int(x) + int(width))
    y1 = min(frame_height, int(y) + int(height))
    if x1 <= x0 or y1 <= y0:
        return np.empty((0, 0), dtype=frame.dtype)
    return frame[y0:y1, x0:x1]


class InterfaceDetector:
    CANONICAL_SIZE = (320, 180)  # (width, height)

    def __init__(self, reference_bgr: np.ndarray, region: tuple | None = None):
        self.region = region
        reference = _to_gray(_to_uint8(reference_bgr))
        self._ref_gray = cv2.resize(
            reference, self.CANONICAL_SIZE, interpolation=cv2.INTER_AREA
        )

    def score(self, frame_bgr: np.ndarray) -> float:
        if frame_bgr is None or frame_bgr.size == 0:
            return 0.0
        frame = _to_uint8(frame_bgr)
        if self.region is not None:
            frame = _crop_region(frame, self.region)
            if frame.size == 0:
                return 0.0
        gray = _to_gray(frame)
        canonical = cv2.resize(gray, self.CANONICAL_SIZE, interpolation=cv2.INTER_AREA)
        result = cv2.matchTemplate(canonical, self._ref_gray, cv2.TM_CCOEFF_NORMED)
        value = float(np.nan_to_num(result[0, 0]))
        return float(np.clip(value, 0.0, 1.0))

    @classmethod
    def from_file(cls, path: str | Path, region: tuple | None = None) -> "InterfaceDetector":
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(f"Cannot read image file: {path}")
        return cls(image, region)
