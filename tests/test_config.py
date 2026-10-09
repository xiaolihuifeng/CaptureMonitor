"""Tests for capture_monitor.config."""

import json

from capture_monitor import paths
from capture_monitor.config import Config


def test_defaults():
    config = Config()
    assert config.reference_image == "DEMO.png"
    assert config.save_dir == ""
    assert config.match_threshold == 0.80
    assert config.match_region is None
    assert config.capture_interval_ms == 1000
    assert config.min_confirm_frames == 2
    assert config.dedup_hamming_threshold == 4
    assert config.monitor_index == 0
    assert config.image_format == "png"
    assert config.auto_start_monitor is True


def test_from_dict_overwrites_known_and_ignores_unknown():
    config = Config.from_dict({"match_threshold": 0.55, "bogus_key": 123})
    assert config.match_threshold == 0.55
    assert config.reference_image == "DEMO.png"  # untouched default
    assert not hasattr(config, "bogus_key")


def test_from_dict_empty_returns_defaults():
    assert Config.from_dict({}) == Config()


def test_save_load_roundtrip(tmp_path):
    original = Config(
        match_threshold=0.9,
        image_format="jpg",
        auto_start_monitor=False,
        match_region=[10, 20, 30, 40],
        capture_interval_ms=500,
    )
    target = tmp_path / "nested" / "config.json"
    original.save(target)
    loaded = Config.load(target)
    assert loaded.to_dict() == original.to_dict()


def test_load_missing_file_writes_defaults(tmp_path):
    target = tmp_path / "fresh.json"
    loaded = Config.load(target)
    assert loaded == Config()
    assert target.exists()


def test_resolved_save_dir_defaults_to_image_dir():
    config = Config()
    assert config.resolved_save_dir() == paths.default_image_dir()


def test_resolved_save_dir_honours_custom_dir(tmp_path):
    config = Config(save_dir=str(tmp_path / "custom"))
    assert config.resolved_save_dir() == tmp_path / "custom"


def test_resolved_reference_finds_demo():
    config = Config()
    assert config.resolved_reference().exists()


def test_load_corrupt_json_returns_defaults(tmp_path):
    target = tmp_path / "broken.json"
    target.write_text("{ not valid json", encoding="utf-8")
    config = Config.load(target)
    assert config == Config()


def test_load_non_object_json_returns_defaults(tmp_path):
    target = tmp_path / "list.json"
    target.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert Config.load(target) == Config()
