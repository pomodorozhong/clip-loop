"""Domain model for clip-loop run configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VideoSegment:
    """One video clip with per-segment processing options."""

    path: Path
    trim_start_ms: int = 0
    speed_percent: float = 100.0
    keep_ratio: float | None = None
    crop_corner: str | None = None
    alternate_reverse: bool = False


@dataclass(frozen=True)
class AudioSegment:
    """One external audio clip with per-segment processing options."""

    path: Path
    trim_start_ms: int = 0
    alternate_reverse: bool = False


@dataclass(frozen=True)
class ClipLoopOptions:
    """Validated configuration for a single clip-loop run."""

    video_segments: tuple[VideoSegment, ...]
    duration: float
    output_path: Path | None = None
    audio_segments: tuple[AudioSegment, ...] = ()
    audio_crossfade_ms: int = 0
    audio_gap_ms: int = 0
    audio_seam_fade_ms: int = 0

    @property
    def input_path(self) -> Path:
        return self.video_segments[0].path

    @property
    def audio_path(self) -> Path | None:
        return self.audio_segments[0].path if self.audio_segments else None

    @property
    def trim_start_ms(self) -> int:
        if len(self.video_segments) == 1:
            return self.video_segments[0].trim_start_ms
        raise AttributeError("trim_start_ms is only defined for a single video segment")

    @property
    def speed_percent(self) -> float:
        if len(self.video_segments) == 1:
            return self.video_segments[0].speed_percent
        raise AttributeError("speed_percent is only defined for a single video segment")

    @property
    def keep_ratio(self) -> float | None:
        if len(self.video_segments) == 1:
            return self.video_segments[0].keep_ratio
        raise AttributeError("keep_ratio is only defined for a single video segment")

    @property
    def crop_corner(self) -> str | None:
        if len(self.video_segments) == 1:
            return self.video_segments[0].crop_corner
        raise AttributeError("crop_corner is only defined for a single video segment")

    @property
    def alternate_reverse(self) -> bool:
        if len(self.video_segments) == 1:
            return self.video_segments[0].alternate_reverse
        raise AttributeError("alternate_reverse is only defined for a single video segment")

    @property
    def audio_alternate_reverse(self) -> bool:
        if len(self.audio_segments) == 1:
            return self.audio_segments[0].alternate_reverse
        raise AttributeError(
            "audio_alternate_reverse is only defined for a single audio segment"
        )

    def to_dict(self) -> dict:
        """Serialize options for persistence (e.g. last-run JSON)."""
        return {
            "video_segments": [
                {
                    "path": str(segment.path),
                    "trim_start_ms": segment.trim_start_ms,
                    "speed_percent": segment.speed_percent,
                    "keep_ratio": segment.keep_ratio,
                    "crop_corner": segment.crop_corner,
                    "alternate_reverse": segment.alternate_reverse,
                }
                for segment in self.video_segments
            ],
            "audio_segments": [
                {
                    "path": str(segment.path),
                    "trim_start_ms": segment.trim_start_ms,
                    "alternate_reverse": segment.alternate_reverse,
                }
                for segment in self.audio_segments
            ],
            "duration": self.duration,
            "output_path": str(self.output_path) if self.output_path else None,
            "audio_crossfade_ms": self.audio_crossfade_ms,
            "audio_gap_ms": self.audio_gap_ms,
            "audio_seam_fade_ms": self.audio_seam_fade_ms,
            "video_input_mode": "multiple" if len(self.video_segments) > 1 else "single",
            "audio_input_mode": "multiple" if len(self.audio_segments) > 1 else "single",
        }

    @classmethod
    def from_dict(cls, data: dict) -> ClipLoopOptions:
        """Deserialize options from a dict (supports legacy flat format)."""
        if "video_segments" in data:
            video_segments = tuple(
                VideoSegment(
                    path=Path(item["path"]),
                    trim_start_ms=int(item.get("trim_start_ms", 0)),
                    speed_percent=float(item.get("speed_percent", 100.0)),
                    keep_ratio=(
                        float(item["keep_ratio"])
                        if item.get("keep_ratio") is not None
                        else None
                    ),
                    crop_corner=item.get("crop_corner"),
                    alternate_reverse=bool(item.get("alternate_reverse", False)),
                )
                for item in data["video_segments"]
            )
            audio_segments = tuple(
                AudioSegment(
                    path=Path(item["path"]),
                    trim_start_ms=int(item.get("trim_start_ms", 0)),
                    alternate_reverse=bool(item.get("alternate_reverse", False)),
                )
                for item in data.get("audio_segments", [])
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
        return cls(
            video_segments=video_segments,
            duration=float(data["duration"]),
            output_path=Path(data["output_path"]) if data.get("output_path") else None,
            audio_segments=audio_segments,
            audio_crossfade_ms=int(data.get("audio_crossfade_ms", 0)),
            audio_gap_ms=int(data.get("audio_gap_ms", 0)),
            audio_seam_fade_ms=int(data.get("audio_seam_fade_ms", 0)),
        )

    @classmethod
    def from_legacy(
        cls,
        *,
        input_path: Path,
        duration: float,
        output_path: Path | None = None,
        alternate_reverse: bool = False,
        trim_start_ms: int = 0,
        audio_path: Path | None = None,
        audio_alternate_reverse: bool = False,
        audio_crossfade_ms: int = 0,
        audio_gap_ms: int = 0,
        audio_seam_fade_ms: int = 0,
        keep_ratio: float | None = None,
        crop_corner: str | None = None,
        speed_percent: float = 100.0,
    ) -> ClipLoopOptions:
        """Build options from the pre-segment flat keyword API."""
        video = VideoSegment(
            path=input_path,
            trim_start_ms=trim_start_ms,
            speed_percent=speed_percent,
            keep_ratio=keep_ratio,
            crop_corner=crop_corner,
            alternate_reverse=alternate_reverse,
        )
        audio_segments: tuple[AudioSegment, ...] = ()
        if audio_path is not None:
            audio_segments = (
                AudioSegment(
                    path=audio_path,
                    alternate_reverse=audio_alternate_reverse,
                ),
            )
        return cls(
            video_segments=(video,),
            duration=duration,
            output_path=output_path,
            audio_segments=audio_segments,
            audio_crossfade_ms=audio_crossfade_ms,
            audio_gap_ms=audio_gap_ms,
            audio_seam_fade_ms=audio_seam_fade_ms,
        )
