"""Tests for clip_loop.options."""

from __future__ import annotations

from pathlib import Path

import pytest

from clip_loop.options import AudioSegment, ClipLoopOptions, VideoSegment


def _sample_options(tmp_path: Path) -> ClipLoopOptions:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"x")
    return ClipLoopOptions(
        video_segments=(
            VideoSegment(
                path=video,
                trim_start_ms=500,
                speed_percent=80.0,
                keep_ratio=0.8,
                crop_corner="top_left",
                alternate_reverse=True,
            ),
        ),
        duration=3600.0,
        output_path=tmp_path / "out.mp4",
        audio_segments=(
            AudioSegment(path=audio, trim_start_ms=100, alternate_reverse=True),
        ),
        audio_crossfade_ms=120,
        audio_gap_ms=50,
        audio_seam_fade_ms=30,
        target_resolution=(1920, 1080),
        fill_mode="fill",
    )


def test_to_dict_from_dict_round_trip(tmp_path: Path) -> None:
    original = _sample_options(tmp_path)
    restored = ClipLoopOptions.from_dict(original.to_dict())
    assert restored == original


def test_from_dict_legacy_flat_format(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"x")
    data = {
        "input_path": str(video),
        "duration": 60.0,
        "audio_path": str(audio),
        "trim_start_ms": 200,
        "speed_percent": 90.0,
        "keep_ratio": 0.5,
        "crop_corner": "bottom_right",
        "alternate_reverse": True,
        "audio_alternate_reverse": True,
        "target_resolution": "1280x720",
        "fill_mode": "fit",
    }
    options = ClipLoopOptions.from_dict(data)
    assert options.input_path == video
    assert options.duration == 60.0
    assert options.audio_path == audio
    assert options.trim_start_ms == 200
    assert options.speed_percent == 90.0
    assert options.keep_ratio == 0.5
    assert options.crop_corner == "bottom_right"
    assert options.target_resolution == (1280, 720)


def test_from_legacy(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    options = ClipLoopOptions.from_legacy(input_path=video, duration=10.0)
    assert options.input_path == video
    assert options.duration == 10.0
    assert len(options.video_segments) == 1


def test_single_segment_property_accessors(tmp_path: Path) -> None:
    options = _sample_options(tmp_path)
    assert options.input_path == options.video_segments[0].path
    assert options.trim_start_ms == 500
    assert options.speed_percent == 80.0
    assert options.keep_ratio == 0.8
    assert options.crop_corner == "top_left"
    assert options.alternate_reverse is True
    assert options.audio_alternate_reverse is True


def test_multi_segment_property_accessors_raise(tmp_path: Path) -> None:
    v1 = tmp_path / "a.mp4"
    v2 = tmp_path / "b.mp4"
    v1.write_bytes(b"x")
    v2.write_bytes(b"x")
    options = ClipLoopOptions(
        video_segments=(VideoSegment(path=v1), VideoSegment(path=v2)),
        duration=10.0,
    )
    with pytest.raises(AttributeError, match="trim_start_ms"):
        _ = options.trim_start_ms
    with pytest.raises(AttributeError, match="speed_percent"):
        _ = options.speed_percent
