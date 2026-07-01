"""Tests for clip_loop.ffmpeg helpers and subprocess functions."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from clip_loop.ffmpeg import (
    build_atempo_chain,
    build_scale_filter,
    default_output_path,
    ffprobe_has_audio,
    run_simple_loop,
    scale_video_to_target,
    trim_video_copy,
    unique_output_path,
)
from clip_loop.media import ffprobe_video_size


def test_default_output_path() -> None:
    assert default_output_path(Path("clip.mp4")) == Path("clip_looped.mp4")


def test_unique_output_path_new_file(tmp_path: Path) -> None:
    path = tmp_path / "out.mp4"
    assert unique_output_path(path) == path


def test_unique_output_path_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "out.mp4"
    path.write_bytes(b"x")
    unique = unique_output_path(path)
    assert unique != path
    assert unique.name.startswith("out_")


@pytest.mark.parametrize("fill_mode", ["fit", "fill"])
def test_build_scale_filter(fill_mode: str) -> None:
    filt = build_scale_filter(1920, 1080, fill_mode)
    assert "scale=1920:1080" in filt
    assert "setsar=1" in filt


def test_build_scale_filter_invalid_mode() -> None:
    with pytest.raises(ValueError):
        build_scale_filter(640, 480, "stretch")


@pytest.mark.parametrize(
    ("factor", "expected_parts"),
    [
        (1.0, ["atempo=1"]),
        (4.0, ["atempo=2", "atempo=2"]),
        (0.25, ["atempo=0.5", "atempo=0.5"]),
    ],
)
def test_build_atempo_chain(factor: float, expected_parts: list[str]) -> None:
    chain = build_atempo_chain(factor)
    for part in expected_parts:
        assert part in chain


def test_ffprobe_has_audio(sample_video: Path, sample_video_noaudio: Path) -> None:
    assert ffprobe_has_audio(sample_video) is True
    assert ffprobe_has_audio(sample_video_noaudio) is False


def test_trim_video_copy(sample_video: Path, tmp_path: Path) -> None:
    out = tmp_path / "trimmed.mp4"
    trim_video_copy(sample_video, out, trim_start_sec=0.5)
    assert out.is_file()
    assert out.stat().st_size > 0


def test_run_simple_loop(sample_video: Path, tmp_path: Path) -> None:
    out = tmp_path / "looped.mp4"
    run_simple_loop(sample_video, out, duration_sec=3.0)
    assert out.is_file()
    assert out.stat().st_size > 0


def test_scale_video_to_target(sample_video: Path, tmp_path: Path) -> None:
    scaled, temps = scale_video_to_target(
        sample_video,
        target_resolution=(160, 120),
        fill_mode="fit",
    )
    try:
        width, height = ffprobe_video_size(scaled)
        assert (width, height) == (160, 120)
    finally:
        for path in temps:
            path.unlink(missing_ok=True)


def test_scale_video_to_target_same_size_skips_encode(sample_video: Path) -> None:
    width, height = ffprobe_video_size(sample_video)
    scaled, temps = scale_video_to_target(
        sample_video,
        target_resolution=(width, height),
        fill_mode="fit",
    )
    assert scaled == sample_video
    assert temps == []
