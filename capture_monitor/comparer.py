"""Perceptual-hash duplicate detection (64-bit dHash).

numpy + cv2 only. The 64-bit hash packs each 8-bit row big-endian, so
``hamming(a, b)`` counts differing bits across the whole 64-bit space.
"""

from __future__ import annotations

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


def dhash(image_bgr: np.ndarray, hash_size: int = 8) -> int:
    gray = _to_gray(_to_uint8(image_bgr))
    resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    result = 0
    for bit in diff.flatten():
        result = (result << 1) | int(bool(bit))
    return result


def hamming(a: int, b: int) -> int:
    return ((a ^ b) & ((1 << 64) - 1)).bit_count()


class ImageComparer:
    def __init__(self, hamming_threshold: int = 4, max_diff: float = 0.008,
                 signature_size: tuple = (64, 36)) -> None:
        self.hamming_threshold = hamming_threshold
        self.max_diff = max_diff
        self.signature_size = signature_size

    def hash(self, image_bgr: np.ndarray) -> int:
        return dhash(image_bgr)

    def is_duplicate(self, h1: int, h2: int) -> bool:
        return hamming(h1, h2) <= self.hamming_threshold

    def signature(self, image_bgr: np.ndarray) -> np.ndarray:
        gray = _to_gray(_to_uint8(image_bgr))
        return cv2.resize(gray, self.signature_size, interpolation=cv2.INTER_AREA).astype(np.float32)

    def difference(self, sig_a: np.ndarray, sig_b: np.ndarray) -> float:
        return float(np.mean(np.abs(sig_a.astype(np.float32) - sig_b.astype(np.float32))) / 255.0)
