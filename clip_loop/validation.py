"""Option validation for clip-loop runs."""

from __future__ import annotations

from clip_loop.errors import ClipLoopError
from clip_loop.media import validate_crop_geometry
from clip_loop.options import AudioSegment, ClipLoopOptions, VideoSegment
from clip_loop.parsing import FILL_MODES


def _video_field(name: str, index: int) -> str:
    return f"video_segments[{index}].{name}"


def _audio_field(name: str, index: int) -> str:
    return f"audio_segments[{index}].{name}"


def validate_video_segment(segment: VideoSegment, *, index: int = 0) -> None:
    if not segment.path.is_file():
        raise ClipLoopError(
            f"Input not found: {segment.path}",
            field=_video_field("path", index),
            segment_index=index,
        )
    if segment.trim_start_ms < 0:
        raise ClipLoopError(
            "Video trim start must be non-negative.",
            field=_video_field("trim_start_ms", index),
            segment_index=index,
        )
    if segment.speed_percent <= 0:
        raise ClipLoopError(
            "Playback speed must be positive.",
            field=_video_field("speed_percent", index),
            segment_index=index,
        )
    if (segment.keep_ratio is None) != (segment.crop_corner is None):
        raise ClipLoopError(
            "Keep ratio and crop corner must be used together.",
            field=_video_field("keep_ratio", index),
            segment_index=index,
        )
    if segment.keep_ratio is not None and segment.crop_corner is not None:
        validate_crop_geometry(
            input_path=segment.path,
            keep_ratio=segment.keep_ratio,
            corner=segment.crop_corner,
            field=_video_field("keep_ratio", index),
            segment_index=index,
        )


def validate_audio_segment(segment: AudioSegment, *, index: int = 0) -> None:
    if not segment.path.is_file():
        raise ClipLoopError(
            f"Audio input not found: {segment.path}",
            field=_audio_field("path", index),
            segment_index=index,
        )
    if segment.trim_start_ms < 0:
        raise ClipLoopError(
            "Audio trim start must be non-negative.",
            field=_audio_field("trim_start_ms", index),
            segment_index=index,
        )


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
        raise ClipLoopError(
            "At least one video segment is required.",
            field="video_segments",
        )
    if options.duration <= 0:
        raise ClipLoopError("Duration must be positive.", field="duration")

    for index, segment in enumerate(options.video_segments):
        validate_video_segment(segment, index=index)

    for index, segment in enumerate(options.audio_segments):
        validate_audio_segment(segment, index=index)

    if options.audio_crossfade_ms < 0:
        raise ClipLoopError(
            "Audio crossfade must be non-negative.",
            field="audio_crossfade_ms",
        )
    if options.audio_crossfade_ms > 0 and not options.audio_segments:
        raise ClipLoopError(
            "Audio crossfade requires at least one audio input.",
            field="audio_crossfade_ms",
        )
    if options.audio_gap_ms < 0:
        raise ClipLoopError(
            "Audio gap must be non-negative.",
            field="audio_gap_ms",
        )
    if options.audio_gap_ms > 0 and not options.audio_segments:
        raise ClipLoopError(
            "Audio gap requires at least one audio input.",
            field="audio_gap_ms",
        )
    if options.audio_seam_fade_ms < 0:
        raise ClipLoopError(
            "Audio seam fade must be non-negative.",
            field="audio_seam_fade_ms",
        )
    if options.audio_seam_fade_ms > 0 and not options.audio_segments:
        raise ClipLoopError(
            "Audio seam fade requires at least one audio input.",
            field="audio_seam_fade_ms",
        )
    if options.fill_mode not in FILL_MODES:
        raise ClipLoopError(
            f"Fill mode must be one of: {', '.join(sorted(FILL_MODES))}.",
            field="fill_mode",
        )
    if options.target_resolution is None and options.fill_mode != "fit":
        raise ClipLoopError(
            "Fill mode requires a target resolution.",
            field="fill_mode",
        )
