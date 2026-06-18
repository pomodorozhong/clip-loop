"""Option validation before processing."""

from __future__ import annotations

import subprocess
from pathlib import Path

from clip_loop.crop import compute_crop_rect
from clip_loop.exceptions import ClipLoopError
from clip_loop.ffmpeg.probe import MediaProbe
from clip_loop.models import ClipLoopOptions
from clip_loop.parsing import CROP_CORNERS


def validate_clip_loop_options(options: ClipLoopOptions, probe: MediaProbe) -> None:
    """Raise ClipLoopError when options are inconsistent or invalid."""
    if not options.input_path.is_file():
        raise ClipLoopError(f"Input not found: {options.input_path}")
    if options.duration <= 0:
        raise ClipLoopError("Duration must be positive.")
    if options.trim_start_ms < 0:
        raise ClipLoopError("--trim-start-ms must be non-negative.")
    if options.speed_percent <= 0:
        raise ClipLoopError("--speed must be positive.")
    if options.audio_path is not None and not options.audio_path.is_file():
        raise ClipLoopError(f"Audio input not found: {options.audio_path}")
    if options.audio_alternate_reverse and options.audio_path is None:
        raise ClipLoopError("--audio-alternate-reverse requires --audio PATH.")
    if options.audio_crossfade_ms < 0:
        raise ClipLoopError("--audio-crossfade-ms must be non-negative.")
    if options.audio_crossfade_ms > 0 and options.audio_path is None:
        raise ClipLoopError("--audio-crossfade-ms requires --audio PATH.")
    if options.audio_gap_ms < 0:
        raise ClipLoopError("--audio-gap-ms must be non-negative.")
    if options.audio_gap_ms > 0 and options.audio_path is None:
        raise ClipLoopError("--audio-gap-ms requires --audio PATH.")
    if options.audio_seam_fade_ms < 0:
        raise ClipLoopError("--audio-seam-fade-ms must be non-negative.")
    if options.audio_seam_fade_ms > 0 and options.audio_path is None:
        raise ClipLoopError("--audio-seam-fade-ms requires --audio PATH.")
    if (options.keep_ratio is None) != (options.crop_corner is None):
        raise ClipLoopError("--keep-ratio and --corner must be used together.")
    if options.keep_ratio is not None and options.crop_corner is not None:
        validate_crop_options(
            probe=probe,
            input_path=options.input_path,
            keep_ratio=options.keep_ratio,
            corner=options.crop_corner,
        )


def validate_crop_options(
    *,
    probe: MediaProbe,
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
        width, height = probe.video_size(input_path)
        compute_crop_rect(width, height, keep_ratio, corner)
    except (subprocess.CalledProcessError, ValueError) as exc:
        raise ClipLoopError(f"Invalid crop for {input_path}: {exc}") from exc
