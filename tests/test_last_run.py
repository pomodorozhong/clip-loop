"""Tests for clip_loop.last_run."""

from __future__ import annotations

from pathlib import Path

import pytest

import clip_loop.last_run as last_run
from clip_loop.last_run import load_last_run, save_last_run
from clip_loop.options import ClipLoopOptions, VideoSegment


def test_save_and_load_last_run_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    path = tmp_path / "last_run.json"
    monkeypatch.setattr(last_run, "LAST_RUN_PATH", path)
    options = ClipLoopOptions(
        video_segments=(VideoSegment(path=video),),
        duration=60.0,
    )
    save_last_run(options)
    loaded = load_last_run()
    assert loaded == options


def test_load_last_run_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(last_run, "LAST_RUN_PATH", tmp_path / "missing.json")
    assert load_last_run() is None


def test_load_last_run_corrupt_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "last_run.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(last_run, "LAST_RUN_PATH", path)
    assert load_last_run() is None
