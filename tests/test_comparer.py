"""Tests for capture_monitor.comparer."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from capture_monitor.comparer import ImageComparer, dhash, hamming

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "DEMO.png"


def _demo_bgr() -> np.ndarray:
    image = cv2.imread(str(DEMO), cv2.IMREAD_COLOR)
    assert image is not None, "DEMO.png must be readable"
    return image


def test_dhash_is_deterministic():
    image = _demo_bgr()
    assert dhash(image) == dhash(image)


def test_dhash_is_64_bit_unsigned():
    value = dhash(_demo_bgr())
    assert 0 <= value < (1 << 64)


def test_hamming_self_is_zero():
    value = dhash(_demo_bgr())
    assert hamming(value, value) == 0


def test_hamming_known_distance():
    # 1 differs from 0 in exactly the lowest bit.
    assert hamming(0, 1) == 1


def test_is_duplicate_same_image_true():
    comparer = ImageComparer()
    image = _demo_bgr()
    hash_1 = comparer.hash(image)
    hash_2 = comparer.hash(image)
    assert comparer.is_duplicate(hash_1, hash_2) is True


def test_is_duplicate_demo_vs_noise_false():
    comparer = ImageComparer()
    demo = _demo_bgr()
    rng = np.random.default_rng(7)
    noise = rng.integers(0, 256, size=demo.shape, dtype=np.uint8)
    assert comparer.is_duplicate(comparer.hash(demo), comparer.hash(noise)) is False


def test_is_duplicate_respects_threshold():
    strict = ImageComparer(hamming_threshold=0)
    assert strict.is_duplicate(0, 0) is True
    assert strict.is_duplicate(0, 1) is False


def test_difference_of_identical_signatures_is_zero():
    comparer = ImageComparer()
    image = _demo_bgr()
    signature = comparer.signature(image)
    assert comparer.difference(signature, comparer.signature(image)) == pytest.approx(0.0)


def test_difference_of_localized_change_exceeds_max_diff():
    comparer = ImageComparer()
    demo = _demo_bgr()
    localized = demo.copy()
    cv2.rectangle(localized, (1450, 160), (1750, 300), (30, 30, 200), -1)
    cv2.putText(localized, "NEW", (1500, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
    signature = comparer.signature(demo)
    changed = comparer.signature(localized)
    assert comparer.difference(signature, changed) > comparer.max_diff
