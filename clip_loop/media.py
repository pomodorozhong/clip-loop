"""ffprobe helpers and crop geometry (no ffmpeg subprocess policy)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from clip_loop.errors import ClipLoopError
from clip_loop.parsing import CROP_CORNERS


def ffprobe_video_size(path: Path) -> tuple[int, int]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    value = r.stdout.strip()
    if not value or "x" not in value:
        raise ValueError(f"ffprobe could not determine video size: {path}")
    width_str, height_str = value.split("x", 1)
    return int(width_str), int(height_str)


def compute_crop_rect(
    width: int,
    height: int,
    keep_ratio: float,
    corner: str,
) -> tuple[int, int, int, int]:
    """Return crop_w, crop_h, x, y for the kept region (even dimensions)."""
    crop_w = int(width * keep_ratio)
    crop_h = int(height * keep_ratio)
    crop_w -= crop_w % 2
    crop_h -= crop_h % 2
    if crop_w <= 0 or crop_h <= 0:
        raise ValueError("keep ratio is too small for this video size")
    if crop_w > width or crop_h > height:
        raise ValueError("keep ratio must be at most 100%")

    if corner == "top_left":
        x = width - crop_w
        y = height - crop_h
    elif corner == "top_right":
        x = 0
        y = height - crop_h
    elif corner == "bottom_left":
        x = width - crop_w
        y = 0
    else:  # bottom_right
        x = 0
        y = 0
    return crop_w, crop_h, x, y


def validate_crop_geometry(
    *,
    input_path: Path,
    keep_ratio: float,
    corner: str,
    field: str | None = None,
    segment_index: int | None = None,
) -> None:
    """Validate crop corner and geometry for a video file."""
    if not input_path.is_file():
        raise ClipLoopError(
            f"Input not found: {input_path}",
            field=field or "video_segments[0].path",
            segment_index=segment_index,
        )
    if corner not in CROP_CORNERS:
        choices = ", ".join(sorted(CROP_CORNERS))
        raise ClipLoopError(
            f"Crop corner must be one of: {choices}",
            field=field or "video_segments[0].crop_corner",
            segment_index=segment_index,
        )
    try:
        width, height = ffprobe_video_size(input_path)
        compute_crop_rect(width, height, keep_ratio, corner)
    except (subprocess.CalledProcessError, ValueError) as exc:
        raise ClipLoopError(
            f"Invalid crop for {input_path}: {exc}",
            field=field or "video_segments[0].keep_ratio",
            segment_index=segment_index,
        ) from exc
