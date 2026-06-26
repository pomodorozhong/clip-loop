"""Option validation for clip-loop runs."""

from __future__ import annotations

import subprocess
from pathlib import Path

from clip_loop.errors import ClipLoopError
from clip_loop.ffmpeg import compute_crop_rect, ffprobe_video_size
from clip_loop.options import AudioSegment, ClipLoopOptions, VideoSegment
from clip_loop.parsing import CROP_CORNERS


def validate_video_segment(segment: VideoSegment) -> None:
    if not segment.path.is_file():
        raise ClipLoopError(f"Input not found: {segment.path}")
    if segment.trim_start_ms < 0:
        raise ClipLoopError("--video-trim-start-ms must be non-negative.")
    if segment.speed_percent <= 0:
        raise ClipLoopError("--video-speed must be positive.")
    if (segment.keep_ratio is None) != (segment.crop_corner is None):
        raise ClipLoopError("--video-keep-ratio and --video-corner must be used together.")
    if segment.keep_ratio is not None and segment.crop_corner is not None:
        validate_crop_options(
            input_path=segment.path,
            keep_ratio=segment.keep_ratio,
            corner=segment.crop_corner,
        )


def validate_audio_segment(segment: AudioSegment) -> None:
    if not segment.path.is_file():
        raise ClipLoopError(f"Audio input not found: {segment.path}")
    if segment.trim_start_ms < 0:
        raise ClipLoopError("--audio-trim-start-ms must be non-negative.")


def validate_clip_loop_options(
    options: ClipLoopOptions | None = None,
    /,
    **kwargs,
) -> None:
    """Validate run options before processing."""
    if options is None:
        if "video_segments" in kwargs:
            options = ClipLoopOptions(**kwargs)
        else:
            options = ClipLoopOptions.from_legacy(**kwargs)
    elif kwargs:
        raise TypeError("pass either ClipLoopOptions or keyword arguments, not both")

    if not options.video_segments:
        raise ClipLoopError("At least one video segment is required.")
    if options.duration <= 0:
        raise ClipLoopError("Duration must be positive.")

    for segment in options.video_segments:
        validate_video_segment(segment)

    for segment in options.audio_segments:
        validate_audio_segment(segment)

    if options.audio_crossfade_ms < 0:
        raise ClipLoopError("--audio-crossfade-ms must be non-negative.")
    if options.audio_crossfade_ms > 0 and not options.audio_segments:
        raise ClipLoopError("--audio-crossfade-ms requires at least one --audio PATH.")
    if options.audio_gap_ms < 0:
        raise ClipLoopError("--audio-gap-ms must be non-negative.")
    if options.audio_gap_ms > 0 and not options.audio_segments:
        raise ClipLoopError("--audio-gap-ms requires at least one --audio PATH.")
    if options.audio_seam_fade_ms < 0:
        raise ClipLoopError("--audio-seam-fade-ms must be non-negative.")
    if options.audio_seam_fade_ms > 0 and not options.audio_segments:
        raise ClipLoopError("--audio-seam-fade-ms requires at least one --audio PATH.")


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
