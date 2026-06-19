"""Persist and restore the last clip-loop TUI run options."""

from __future__ import annotations

import json
from pathlib import Path

from clip_loop.options import ClipLoopOptions

LAST_RUN_PATH = Path.home() / ".config" / "clip-loop" / "last_run.json"


def save_last_run(options: ClipLoopOptions) -> None:
    """Write *options* to the user's config directory."""
    LAST_RUN_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "input_path": str(options.input_path),
        "duration": options.duration,
        "output_path": str(options.output_path) if options.output_path else None,
        "alternate_reverse": options.alternate_reverse,
        "trim_start_ms": options.trim_start_ms,
        "audio_path": str(options.audio_path) if options.audio_path else None,
        "audio_alternate_reverse": options.audio_alternate_reverse,
        "audio_crossfade_ms": options.audio_crossfade_ms,
        "audio_gap_ms": options.audio_gap_ms,
        "audio_seam_fade_ms": options.audio_seam_fade_ms,
        "keep_ratio": options.keep_ratio,
        "crop_corner": options.crop_corner,
        "speed_percent": options.speed_percent,
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
        return ClipLoopOptions(
            input_path=Path(data["input_path"]),
            duration=float(data["duration"]),
            output_path=Path(data["output_path"]) if data.get("output_path") else None,
            alternate_reverse=bool(data.get("alternate_reverse", False)),
            trim_start_ms=int(data.get("trim_start_ms", 0)),
            audio_path=Path(data["audio_path"]) if data.get("audio_path") else None,
            audio_alternate_reverse=bool(data.get("audio_alternate_reverse", False)),
            audio_crossfade_ms=int(data.get("audio_crossfade_ms", 0)),
            audio_gap_ms=int(data.get("audio_gap_ms", 0)),
            audio_seam_fade_ms=int(data.get("audio_seam_fade_ms", 0)),
            keep_ratio=(
                float(data["keep_ratio"]) if data.get("keep_ratio") is not None else None
            ),
            crop_corner=data.get("crop_corner"),
            speed_percent=float(data.get("speed_percent", 100.0)),
        )
    except (KeyError, TypeError, ValueError):
        return None
