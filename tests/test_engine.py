"""Tests for capture_monitor.engine (Qt-free, headless-safe)."""

from __future__ import annotations

import os
import time
from pathlib import Path

import cv2
import numpy as np

from capture_monitor.config import Config
from capture_monitor.detector import InterfaceDetector
from capture_monitor.engine import (
    REASON_DUPLICATE,
    REASON_NO_INTERFACE,
    REASON_PENDING,
    REASON_SAVED,
    MonitorEngine,
)

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "DEMO.png"


def _demo_bgr() -> np.ndarray:
    image = cv2.imread(str(DEMO), cv2.IMREAD_COLOR)
    assert image is not None, "DEMO.png must be readable"
    return image


def _build_engine(tmp_path: Path, on_captured=None, **overrides) -> tuple[Config, MonitorEngine]:
    config = Config(save_dir=str(tmp_path), match_threshold=0.80, min_confirm_frames=2)
    for key, value in overrides.items():
        setattr(config, key, value)
    detector = InterfaceDetector.from_file(DEMO)
    engine = MonitorEngine(config, detector, on_captured=on_captured)
    return config, engine


def _modified_demo(demo: np.ndarray) -> np.ndarray:
    """Fill two big blocks with their local mean color.

    Solid black rectangles would drop the template-match score below the
    threshold, so each block is filled with its own mean color instead: the
    overall correlation stays high while the dHash changes enough to pass the
    duplicate filter.
    """
    modified = demo.copy()
    height, width = modified.shape[:2]
    block = modified[0:450, 0:600]
    modified[0:450, 0:600] = block.mean(axis=(0, 1)).astype(np.uint8)
    block = modified[height // 2 : height // 2 + 200, width // 2 : width // 2 + 300]
    modified[height // 2 : height // 2 + 200, width // 2 : width // 2 + 300] = (
        block.mean(axis=(0, 1)).astype(np.uint8)
    )
    return modified


class _Collector:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, path: str, meta: dict) -> None:
        self.calls.append((path, meta))


def test_tick_no_interface_on_noise_frame(tmp_path):
    _, engine = _build_engine(tmp_path)
    rng = np.random.default_rng(0)
    noise = rng.integers(0, 256, size=(1080, 1920, 3), dtype=np.uint8)
    result = engine.tick(noise)
    assert result.reason == REASON_NO_INTERFACE
    assert result.saved is False
    assert result.path is None


def test_tick_pending_before_confirmation(tmp_path):
    _, engine = _build_engine(tmp_path)
    result = engine.tick(_demo_bgr())
    assert result.reason == REASON_PENDING
    assert result.saved is False


def test_tick_saves_after_confirmation(tmp_path):
    collector = _Collector()
    _, engine = _build_engine(tmp_path, on_captured=collector)
    demo = _demo_bgr()
    first = engine.tick(demo)
    assert first.reason == REASON_PENDING
    result = engine.tick(demo)
    assert result.reason == REASON_SAVED
    assert result.saved is True
    assert result.path is not None
    saved_path = Path(result.path)
    assert saved_path.exists()
    assert saved_path.name.startswith("cap_")
    assert saved_path.name.endswith(".png")
    assert len(collector.calls) == 1
    assert collector.calls[0][0] == result.path


def test_tick_duplicate_after_save(tmp_path):
    _, engine = _build_engine(tmp_path)
    demo = _demo_bgr()
    engine.tick(demo)
    saved = engine.tick(demo)
    assert saved.reason == REASON_SAVED
    duplicate = engine.tick(demo)
    assert duplicate.reason == REASON_DUPLICATE
    assert duplicate.saved is False
    assert len(engine.captured) == 1


def test_tick_changed_frame_saves_again(tmp_path):
    _, engine = _build_engine(tmp_path)
    demo = _demo_bgr()
    engine.tick(demo)
    engine.tick(demo)
    result = engine.tick(_modified_demo(demo))
    assert result.reason == REASON_SAVED
    assert result.saved is True
    assert Path(result.path).exists()
    assert len(engine.captured) == 2


def test_tick_localized_change_saves(tmp_path):
    _, engine = _build_engine(tmp_path)
    demo = _demo_bgr()
    engine.tick(demo)
    engine.tick(demo)
    localized = demo.copy()
    cv2.rectangle(localized, (1450, 160), (1750, 300), (30, 30, 200), -1)
    cv2.putText(localized, "NEW", (1500, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
    assert engine.detector.score(localized) >= engine.config.match_threshold
    result = engine.tick(localized)
    assert result.reason == REASON_SAVED
    assert len(engine.captured) == 2


def test_reset_restarts_confirmation(tmp_path):
    _, engine = _build_engine(tmp_path)
    demo = _demo_bgr()
    engine.tick(demo)
    engine.tick(demo)
    engine.reset()
    first = engine.tick(demo)
    assert first.reason == REASON_PENDING
    second = engine.tick(demo)
    assert second.reason == REASON_SAVED


def test_jpg_image_format_saves_jpg(tmp_path):
    _, engine = _build_engine(tmp_path, image_format="jpg")
    demo = _demo_bgr()
    engine.tick(demo)
    result = engine.tick(demo)
    assert result.reason == REASON_SAVED
    assert result.path is not None
    assert result.path.endswith(".jpg")
    assert Path(result.path).exists()


def test_scan_existing_returns_files_newest_first(tmp_path):
    config, engine = _build_engine(tmp_path)
    demo = _demo_bgr()
    engine.tick(demo)
    first_saved = engine.tick(demo)
    second_saved = engine.tick(_modified_demo(demo))
    assert first_saved.saved and second_saved.saved

    base = time.time()
    os.utime(first_saved.path, (base + 10, base + 10))
    os.utime(second_saved.path, (base + 20, base + 20))

    fresh = MonitorEngine(config, InterfaceDetector.from_file(DEMO))
    entries = fresh.scan_existing()
    assert [entry["path"] for entry in entries] == [second_saved.path, first_saved.path]
    for entry in entries:
        assert entry["score"] is None
        assert entry["name"] == Path(entry["path"]).name
        assert Path(entry["path"]).exists()


def test_scan_existing_seeds_dedup_after_restart(tmp_path):
    config, engine = _build_engine(tmp_path)
    demo = _demo_bgr()
    engine.tick(demo)
    engine.tick(demo)

    fresh = MonitorEngine(config, InterfaceDetector.from_file(DEMO))
    fresh.scan_existing()
    first = fresh.tick(demo)
    assert first.reason == REASON_PENDING
    second = fresh.tick(demo)
    assert second.reason == REASON_DUPLICATE


def test_capture_now_force_saves(tmp_path):
    _, engine = _build_engine(tmp_path)
    rng = np.random.default_rng(1)
    noise = rng.integers(0, 256, size=(1080, 1920, 3), dtype=np.uint8)
    result = engine.capture_now(noise)
    assert result.saved is True and result.reason == "manual"
    assert result.path is not None and Path(result.path).exists()


def test_capture_now_updates_dedup_baseline(tmp_path):
    _, engine = _build_engine(tmp_path)
    demo = _demo_bgr()
    engine.capture_now(demo)
    engine.tick(demo)
    assert engine.tick(demo).reason == REASON_DUPLICATE
