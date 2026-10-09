"""Tests for capture_monitor.detector."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from capture_monitor.detector import InterfaceDetector

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "DEMO.png"


@pytest.fixture(scope="module")
def demo_bgr() -> np.ndarray:
    image = cv2.imread(str(DEMO), cv2.IMREAD_COLOR)
    assert image is not None, "DEMO.png must be readable"
    return image


def test_from_file_raises_for_missing_path():
    with pytest.raises(FileNotFoundError):
        InterfaceDetector.from_file(ROOT / "does_not_exist.png")


def test_score_high_on_identical_reference(demo_bgr):
    detector = InterfaceDetector.from_file(DEMO)
    assert detector.score(demo_bgr) > 0.9


def test_score_low_on_random_noise(demo_bgr):
    detector = InterfaceDetector.from_file(DEMO)
    rng = np.random.default_rng(42)
    noise = rng.integers(0, 256, size=demo_bgr.shape, dtype=np.uint8)
    assert detector.score(noise) < 0.5


def test_score_low_on_blank_gray_frame(demo_bgr):
    detector = InterfaceDetector.from_file(DEMO)
    blank = np.full(demo_bgr.shape[:2], 128, dtype=np.uint8)
    assert detector.score(blank) < 0.9


def test_score_returns_zero_for_empty_frame():
    detector = InterfaceDetector.from_file(DEMO)
    assert detector.score(np.zeros((0, 0, 3), dtype=np.uint8)) == 0.0


def test_score_returns_zero_for_none_frame():
    detector = InterfaceDetector.from_file(DEMO)
    assert detector.score(None) == 0.0


def test_score_with_region_crops_frame(demo_bgr):
    detector = InterfaceDetector.from_file(DEMO, region=(100, 50, 400, 300))
    assert 0.0 <= detector.score(demo_bgr) <= 1.0


def test_score_with_out_of_bounds_region_returns_zero(demo_bgr):
    detector = InterfaceDetector.from_file(DEMO, region=(10_000, 10_000, 400, 300))
    assert detector.score(demo_bgr) == 0.0


def test_score_handles_float_frame(demo_bgr):
    detector = InterfaceDetector.from_file(DEMO)
    float_frame = demo_bgr.astype(np.float32) / 255.0
    assert detector.score(float_frame) > 0.9
