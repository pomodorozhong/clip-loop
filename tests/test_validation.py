"""Tests for clip_loop.validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from clip_loop.errors import ClipLoopError
from clip_loop.options import AudioSegment, ClipLoopOptions, VideoSegment
from clip_loop.validation import (
    validate_audio_segment,
    validate_clip_loop_options,
    validate_video_segment,
)


def test_validate_video_segment_missing_file(tmp_path: Path) -> None:
    segment = VideoSegment(path=tmp_path / "missing.mp4")
    with pytest.raises(ClipLoopError, match="Input not found") as exc_info:
        validate_video_segment(segment)
    assert exc_info.value.field == "video_segments[0].path"


def test_validate_video_segment_negative_trim(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    segment = VideoSegment(path=video, trim_start_ms=-1)
    with pytest.raises(ClipLoopError, match="trim start") as exc_info:
        validate_video_segment(segment)
    assert exc_info.value.field == "video_segments[0].trim_start_ms"


def test_validate_video_segment_invalid_speed(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    segment = VideoSegment(path=video, speed_percent=0)
    with pytest.raises(ClipLoopError, match="speed must be positive"):
        validate_video_segment(segment)


def test_validate_video_segment_crop_pair_required(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    segment = VideoSegment(path=video, keep_ratio=0.8, crop_corner=None)
    with pytest.raises(ClipLoopError, match="together"):
        validate_video_segment(segment)


@patch("clip_loop.media.ffprobe_video_size", return_value=(320, 240))
def test_validate_video_segment_crop_geometry(
    _mock_size: object, tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    segment = VideoSegment(
        path=video, keep_ratio=0.8, crop_corner="top_left"
    )
    validate_video_segment(segment)


def test_validate_audio_segment_missing_file(tmp_path: Path) -> None:
    segment = AudioSegment(path=tmp_path / "missing.m4a")
    with pytest.raises(ClipLoopError, match="Audio input not found"):
        validate_audio_segment(segment)


def test_validate_clip_loop_options_no_video(tmp_path: Path) -> None:
    with pytest.raises(ClipLoopError, match="At least one video"):
        validate_clip_loop_options(video_segments=(), duration=10.0)


def test_validate_clip_loop_options_invalid_duration(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    with pytest.raises(ClipLoopError, match="Duration must be positive"):
        validate_clip_loop_options(
            video_segments=(VideoSegment(path=video),),
            duration=0,
        )


def test_validate_clip_loop_options_audio_seam_requires_audio(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    options = ClipLoopOptions(
        video_segments=(VideoSegment(path=video),),
        duration=10.0,
        audio_crossfade_ms=100,
    )
    with pytest.raises(ClipLoopError, match="crossfade requires"):
        validate_clip_loop_options(options)


def test_validate_clip_loop_options_fill_requires_resolution(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    options = ClipLoopOptions(
        video_segments=(VideoSegment(path=video),),
        duration=10.0,
        fill_mode="fill",
        target_resolution=None,
    )
    with pytest.raises(ClipLoopError, match="Fill mode requires"):
        validate_clip_loop_options(options)


def test_validate_clip_loop_options_kwargs_and_instance_conflict(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    options = ClipLoopOptions(
        video_segments=(VideoSegment(path=video),),
        duration=10.0,
    )
    with pytest.raises(TypeError):
        validate_clip_loop_options(options, duration=20.0)
