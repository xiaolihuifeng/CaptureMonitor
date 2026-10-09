"""Tests for capture_monitor.paths."""

from capture_monitor import paths


def test_program_dir_is_project_root():
    assert paths.program_dir().name == "CaptureMonitor"


def test_default_image_dir_named_image():
    assert paths.default_image_dir().name == "Image"


def test_config_path_under_program_dir():
    assert paths.config_path() == paths.program_dir() / "config.json"


def test_log_path_under_program_dir():
    assert paths.log_path() == paths.program_dir() / "CaptureMonitor.log"


def test_resolve_reference_finds_existing_demo_png():
    resolved = paths.resolve_reference("DEMO.png")
    assert resolved.exists() is True
    assert resolved.name == "DEMO.png"


def test_resolve_reference_absolute_path_returned_as_is(tmp_path):
    absolute = (tmp_path / "DEMO.png").resolve()
    absolute.write_bytes(b"placeholder")
    assert paths.resolve_reference(str(absolute)) == absolute


def test_resolve_reference_missing_falls_back_to_program_dir():
    resolved = paths.resolve_reference("definitely_missing_xyz.png")
    assert resolved == paths.program_dir() / "definitely_missing_xyz.png"


def test_resource_dir_equals_program_dir_when_not_frozen():
    assert paths.resource_dir() == paths.program_dir()


def test_is_frozen_false_when_not_packaged():
    assert paths.is_frozen() is False
