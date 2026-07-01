"""Tests for clip_loop.cli."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from clip_loop.cli import _namespace_to_options, build_parser, main
from clip_loop.errors import ClipLoopError
from clip_loop.options import VideoSegment
from clip_loop.parsing import parse_duration
from clip_loop.segment_argv import ParsedSegments


def test_build_parser_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args(["video.mp4"])
    assert args.duration == parse_duration("1h")
    assert args.speed == 100.0
    assert args.trim_start_ms == 0


def test_namespace_to_options_positional(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    parser = build_parser()
    args = parser.parse_args([str(video), "-d", "30s"])
    segments = ParsedSegments()
    options = _namespace_to_options(args, segments)
    assert options.video_segments[0].path == video
    assert options.duration == 30.0


def test_namespace_to_options_video_flag(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    parser = build_parser()
    args = parser.parse_args(["-d", "10s"])
    segments = ParsedSegments(video_segments=[VideoSegment(path=video)])
    options = _namespace_to_options(args, segments)
    assert options.video_segments[0].path == video


def test_namespace_to_options_conflicting_input(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    parser = build_parser()
    args = parser.parse_args([str(video)])
    segments = ParsedSegments(video_segments=[VideoSegment(path=video)])
    with pytest.raises(ClipLoopError, match="Cannot combine"):
        _namespace_to_options(args, segments)


def test_namespace_to_options_fill_requires_resolution(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    parser = build_parser()
    args = parser.parse_args([str(video), "--fill"])
    segments = ParsedSegments()
    with pytest.raises(ClipLoopError, match="require --resolution"):
        _namespace_to_options(args, segments)


def test_main_clip_loop_error_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    monkeypatch.setattr(sys, "argv", ["clip-loop", str(video), "-d", "5s"])
    monkeypatch.setattr(
        "clip_loop.cli.run_clip_loop",
        MagicMock(side_effect=ClipLoopError("boom")),
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


def test_main_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    out = tmp_path / "out.mp4"
    monkeypatch.setattr(sys, "argv", ["clip-loop", str(video), "-d", "5s"])
    monkeypatch.setattr("clip_loop.cli.run_clip_loop", MagicMock(return_value=out))
    main()
    captured = capsys.readouterr()
    assert "Wrote" in captured.out
