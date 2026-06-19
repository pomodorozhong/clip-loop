"""Option validation for clip-loop runs."""

from __future__ import annotations

import subprocess
from pathlib import Path

from clip_loop.errors import ClipLoopError
from clip_loop.ffmpeg import compute_crop_rect, ffprobe_video_size
from clip_loop.options import ClipLoopOptions
from clip_loop.parsing import CROP_CORNERS


def validate_clip_loop_options(
    options: ClipLoopOptions | None = None,
    /,
    **kwargs,
) -> None:
    """Validate run options before processing."""
    if options is None:
        options = ClipLoopOptions(**kwargs)
    elif kwargs:
        raise TypeError("pass either ClipLoopOptions or keyword arguments, not both")

    input_path = options.input_path
    duration = options.duration
    trim_start_ms = options.trim_start_ms
    audio_path = options.audio_path
    audio_alternate_reverse = options.audio_alternate_reverse
    audio_crossfade_ms = options.audio_crossfade_ms
    audio_gap_ms = options.audio_gap_ms
    audio_seam_fade_ms = options.audio_seam_fade_ms
    keep_ratio = options.keep_ratio
    crop_corner = options.crop_corner
    speed_percent = options.speed_percent

    if not input_path.is_file():
        raise ClipLoopError(f"Input not found: {input_path}")
    if duration <= 0:
        raise ClipLoopError("Duration must be positive.")
    if trim_start_ms < 0:
        raise ClipLoopError("--trim-start-ms must be non-negative.")
    if speed_percent <= 0:
        raise ClipLoopError("--speed must be positive.")
    if audio_path is not None and not audio_path.is_file():
        raise ClipLoopError(f"Audio input not found: {audio_path}")
    if audio_alternate_reverse and audio_path is None:
        raise ClipLoopError("--audio-alternate-reverse requires --audio PATH.")
    if audio_crossfade_ms < 0:
        raise ClipLoopError("--audio-crossfade-ms must be non-negative.")
    if audio_crossfade_ms > 0 and audio_path is None:
        raise ClipLoopError("--audio-crossfade-ms requires --audio PATH.")
    if audio_gap_ms < 0:
        raise ClipLoopError("--audio-gap-ms must be non-negative.")
    if audio_gap_ms > 0 and audio_path is None:
        raise ClipLoopError("--audio-gap-ms requires --audio PATH.")
    if audio_seam_fade_ms < 0:
        raise ClipLoopError("--audio-seam-fade-ms must be non-negative.")
    if audio_seam_fade_ms > 0 and audio_path is None:
        raise ClipLoopError("--audio-seam-fade-ms requires --audio PATH.")
    if (keep_ratio is None) != (crop_corner is None):
        raise ClipLoopError("--keep-ratio and --corner must be used together.")
    if keep_ratio is not None and crop_corner is not None:
        validate_crop_options(
            input_path=input_path,
            keep_ratio=keep_ratio,
            corner=crop_corner,
        )


def validate_crop_options(
    *,
    input_path: Path,
    keep_ratio: float,
    corner: str,
) -> None:
    if not input_path.is_file():
        raise ClipLoopError(f"Input not found: {input_path}")
    if corner not in CROP_CORNERS:
        choices = ", ".join(sorted(CROP_CORNERS))
        raise ClipLoopError(f"--corner must be one of: {choices}")
    try:
        width, height = ffprobe_video_size(input_path)
        compute_crop_rect(width, height, keep_ratio, corner)
    except (subprocess.CalledProcessError, ValueError) as exc:
        raise ClipLoopError(f"Invalid crop for {input_path}: {exc}") from exc
