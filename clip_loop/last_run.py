"""Persist and restore the last clip-loop TUI run options."""

from __future__ import annotations

import json
from pathlib import Path

from clip_loop.options import AudioSegment, ClipLoopOptions, VideoSegment

LAST_RUN_PATH = Path.home() / ".config" / "clip-loop" / "last_run.json"


def _video_segment_to_dict(segment: VideoSegment) -> dict:
    return {
        "path": str(segment.path),
        "trim_start_ms": segment.trim_start_ms,
        "speed_percent": segment.speed_percent,
        "keep_ratio": segment.keep_ratio,
        "crop_corner": segment.crop_corner,
        "alternate_reverse": segment.alternate_reverse,
    }


def _audio_segment_to_dict(segment: AudioSegment) -> dict:
    return {
        "path": str(segment.path),
        "trim_start_ms": segment.trim_start_ms,
        "alternate_reverse": segment.alternate_reverse,
    }


def _video_segment_from_dict(data: dict) -> VideoSegment:
    return VideoSegment(
        path=Path(data["path"]),
        trim_start_ms=int(data.get("trim_start_ms", 0)),
        speed_percent=float(data.get("speed_percent", 100.0)),
        keep_ratio=(
            float(data["keep_ratio"]) if data.get("keep_ratio") is not None else None
        ),
        crop_corner=data.get("crop_corner"),
        alternate_reverse=bool(data.get("alternate_reverse", False)),
    )


def _audio_segment_from_dict(data: dict) -> AudioSegment:
    return AudioSegment(
        path=Path(data["path"]),
        trim_start_ms=int(data.get("trim_start_ms", 0)),
        alternate_reverse=bool(data.get("alternate_reverse", False)),
    )


def save_last_run(options: ClipLoopOptions) -> None:
    """Write *options* to the user's config directory."""
    LAST_RUN_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "video_segments": [_video_segment_to_dict(s) for s in options.video_segments],
        "audio_segments": [_audio_segment_to_dict(s) for s in options.audio_segments],
        "duration": options.duration,
        "output_path": str(options.output_path) if options.output_path else None,
        "audio_crossfade_ms": options.audio_crossfade_ms,
        "audio_gap_ms": options.audio_gap_ms,
        "audio_seam_fade_ms": options.audio_seam_fade_ms,
        "video_input_mode": "multiple" if len(options.video_segments) > 1 else "single",
        "audio_input_mode": "multiple" if len(options.audio_segments) > 1 else "single",
    }
    LAST_RUN_PATH.write_text(json.dumps(data, indent=2) + "\n")


def load_last_run() -> ClipLoopOptions | None:
    """Load the most recently saved run options, if any."""
    if not LAST_RUN_PATH.is_file():
        return None
    try:
        data = json.loads(LAST_RUN_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    try:
        if "video_segments" in data:
            video_segments = tuple(
                _video_segment_from_dict(item) for item in data["video_segments"]
            )
            audio_segments = tuple(
                _audio_segment_from_dict(item) for item in data.get("audio_segments", [])
            )
        else:
            video_segments = (
                VideoSegment(
                    path=Path(data["input_path"]),
                    trim_start_ms=int(data.get("trim_start_ms", 0)),
                    speed_percent=float(data.get("speed_percent", 100.0)),
                    keep_ratio=(
                        float(data["keep_ratio"])
                        if data.get("keep_ratio") is not None
                        else None
                    ),
                    crop_corner=data.get("crop_corner"),
                    alternate_reverse=bool(data.get("alternate_reverse", False)),
                ),
            )
            audio_segments = ()
            if data.get("audio_path"):
                audio_segments = (
                    AudioSegment(
                        path=Path(data["audio_path"]),
                        alternate_reverse=bool(data.get("audio_alternate_reverse", False)),
                    ),
                )
        return ClipLoopOptions(
            video_segments=video_segments,
            duration=float(data["duration"]),
            output_path=Path(data["output_path"]) if data.get("output_path") else None,
            audio_segments=audio_segments,
            audio_crossfade_ms=int(data.get("audio_crossfade_ms", 0)),
            audio_gap_ms=int(data.get("audio_gap_ms", 0)),
            audio_seam_fade_ms=int(data.get("audio_seam_fade_ms", 0)),
        )
    except (KeyError, TypeError, ValueError):
        return None
