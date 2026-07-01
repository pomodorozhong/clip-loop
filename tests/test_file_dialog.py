"""Tests for clip_loop.file_dialog pure helpers."""

from __future__ import annotations

from pathlib import Path

from clip_loop.file_dialog import _escape_applescript, _resolve_start


def test_escape_applescript() -> None:
    assert _escape_applescript('say "hello"') == 'say \\"hello\\"'
    assert _escape_applescript("back\\slash") == "back\\\\slash"


def test_resolve_start_none() -> None:
    assert _resolve_start(None) == Path.home()


def test_resolve_start_directory(tmp_path: Path) -> None:
    assert _resolve_start(tmp_path) == tmp_path


def test_resolve_start_file(tmp_path: Path) -> None:
    file_path = tmp_path / "clip.mp4"
    file_path.write_bytes(b"x")
    assert _resolve_start(file_path) == tmp_path


def test_resolve_start_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing" / "clip.mp4"
    # Parent directory does not exist; falls back to home.
    assert _resolve_start(missing) == Path.home()
