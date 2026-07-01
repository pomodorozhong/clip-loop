"""Tests for clip_loop.media."""

from __future__ import annotations

from pathlib import Path

import pytest

from clip_loop.media import compute_crop_rect, ffprobe_video_size, validate_crop_geometry


@pytest.mark.parametrize(
    ("corner", "expected_xy"),
    [
        ("top_left", (40, 20)),
        ("top_right", (0, 20)),
        ("bottom_left", (40, 0)),
        ("bottom_right", (0, 0)),
    ],
)
def test_compute_crop_rect_corners(
    corner: str, expected_xy: tuple[int, int]
) -> None:
    crop_w, crop_h, x, y = compute_crop_rect(200, 100, 0.8, corner)
    assert crop_w % 2 == 0
    assert crop_h % 2 == 0
    assert (x, y) == expected_xy


def test_compute_crop_rect_even_dimensions() -> None:
    crop_w, crop_h, _, _ = compute_crop_rect(201, 101, 0.5, "top_left")
    assert crop_w % 2 == 0
    assert crop_h % 2 == 0


def test_compute_crop_rect_ratio_too_small() -> None:
    with pytest.raises(ValueError, match="too small"):
        compute_crop_rect(10, 10, 0.01, "top_left")


def test_compute_crop_rect_ratio_too_large() -> None:
    with pytest.raises(ValueError, match="at most 100%"):
        compute_crop_rect(100, 100, 1.5, "top_left")


def test_ffprobe_video_size(sample_video: Path) -> None:
    width, height = ffprobe_video_size(sample_video)
    assert width == 320
    assert height == 240


def test_validate_crop_geometry(sample_video: Path) -> None:
    validate_crop_geometry(
        input_path=sample_video,
        keep_ratio=0.8,
        corner="top_left",
    )
