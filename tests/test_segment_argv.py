"""Tests for clip_loop.segment_argv."""

from __future__ import annotations

from pathlib import Path

import pytest

from clip_loop.errors import ClipLoopError
from clip_loop.segment_argv import parse_segment_argv


def test_parse_single_video_and_remaining_argv() -> None:
    result = parse_segment_argv(["--video", "a.mp4", "-d", "30s"])
    assert len(result.video_segments) == 1
    assert result.video_segments[0].path == Path("a.mp4")
    assert result.remaining_argv == ["-d", "30s"]


def test_parse_video_with_options() -> None:
    result = parse_segment_argv(
        [
            "--video",
            "a.mp4",
            "--video-trim-start-ms",
            "500",
            "--video-speed",
            "80%",
            "--video-keep-ratio",
            "50%",
            "--video-corner",
            "top_right",
            "--video-alternate-reverse",
        ]
    )
    seg = result.video_segments[0]
    assert seg.trim_start_ms == 500
    assert seg.speed_percent == 80.0
    assert seg.keep_ratio == 0.5
    assert seg.crop_corner == "top_right"
    assert seg.alternate_reverse is True


def test_parse_multiple_videos_flush_on_new_video() -> None:
    result = parse_segment_argv(["--video", "a.mp4", "--video", "b.mp4"])
    assert len(result.video_segments) == 2
    assert result.video_segments[0].path == Path("a.mp4")
    assert result.video_segments[1].path == Path("b.mp4")


def test_parse_audio_segment() -> None:
    result = parse_segment_argv(
        [
            "--audio",
            "x.m4a",
            "--audio-trim-start-ms",
            "100",
            "--audio-alternate-reverse",
        ]
    )
    assert len(result.audio_segments) == 1
    audio = result.audio_segments[0]
    assert audio.path == Path("x.m4a")
    assert audio.trim_start_ms == 100
    assert audio.alternate_reverse is True


@pytest.mark.parametrize(
    ("argv", "match"),
    [
        (["--video"], "requires a PATH"),
        (["--video-trim-start-ms", "0"], "must follow --video"),
        (["--video", "a.mp4", "--audio-trim-start-ms", "0"], "must follow --audio"),
        (["--video-speed", "100"], "must follow --video"),
    ],
)
def test_parse_segment_argv_errors(argv: list[str], match: str) -> None:
    with pytest.raises(ClipLoopError, match=match):
        parse_segment_argv(argv)
