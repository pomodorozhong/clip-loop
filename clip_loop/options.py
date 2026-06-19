"""Domain model for clip-loop run configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClipLoopOptions:
    """Validated configuration for a single clip-loop run."""

    input_path: Path
    duration: float
    output_path: Path | None = None
    alternate_reverse: bool = False
    trim_start_ms: int = 0
    audio_path: Path | None = None
    audio_alternate_reverse: bool = False
    audio_crossfade_ms: int = 0
    audio_gap_ms: int = 0
    audio_seam_fade_ms: int = 0
    keep_ratio: float | None = None
    crop_corner: str | None = None
    speed_percent: float = 100.0

    def as_run_kwargs(self) -> dict:
        """Keyword arguments for :func:`clip_loop.pipeline.run_clip_loop`."""
        return {
            "input_path": self.input_path,
            "duration": self.duration,
            "output_path": self.output_path,
            "alternate_reverse": self.alternate_reverse,
            "trim_start_ms": self.trim_start_ms,
            "audio_path": self.audio_path,
            "audio_alternate_reverse": self.audio_alternate_reverse,
            "audio_crossfade_ms": self.audio_crossfade_ms,
            "audio_gap_ms": self.audio_gap_ms,
            "audio_seam_fade_ms": self.audio_seam_fade_ms,
            "keep_ratio": self.keep_ratio,
            "crop_corner": self.crop_corner,
            "speed_percent": self.speed_percent,
        }
