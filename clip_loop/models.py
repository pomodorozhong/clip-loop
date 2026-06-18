"""Domain models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClipLoopOptions:
    """All inputs required to loop a clip to a target duration."""

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

    @property
    def trim_start_sec(self) -> float:
        return self.trim_start_ms / 1000.0

    @property
    def audio_crossfade_sec(self) -> float:
        return self.audio_crossfade_ms / 1000.0

    @property
    def audio_gap_sec(self) -> float:
        return self.audio_gap_ms / 1000.0

    @property
    def audio_seam_fade_sec(self) -> float:
        return self.audio_seam_fade_ms / 1000.0


@dataclass(frozen=True)
class AudioEffectOptions:
    """External-audio processing flags shared by loop strategies."""

    alternate_reverse: bool
    gap_sec: float
    crossfade_sec: float
    seam_fade_sec: float
