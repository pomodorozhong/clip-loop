"""Parse and format user-supplied option values."""

from __future__ import annotations

from pathlib import Path

from clip_loop.exceptions import ParseError

CROP_CORNERS = frozenset({"top_left", "top_right", "bottom_left", "bottom_right"})


def parse_duration(value: str) -> float:
    """Parse duration: plain number = seconds, or suffix h/m/s (e.g. 1h, 30m, 90s)."""
    s = value.strip().lower()
    if not s:
        raise ParseError("duration cannot be empty")
    if s.endswith("h"):
        return float(s[:-1]) * 3600
    if s.endswith("m"):
        return float(s[:-1]) * 60
    if s.endswith("s"):
        return float(s[:-1])
    return float(s)


def parse_keep_ratio(value: str) -> float:
    """Parse keep ratio: 80%, 50%, 0.8, or 80 (percent)."""
    s = value.strip().lower()
    if not s:
        raise ParseError("keep ratio cannot be empty")
    if s.endswith("%"):
        ratio = float(s[:-1]) / 100.0
    else:
        ratio = float(s)
        if ratio > 1.0:
            ratio /= 100.0
    if not 0.0 < ratio <= 1.0:
        raise ParseError("keep ratio must be between 0 and 100%")
    return ratio


def parse_crop_corner(value: str) -> str:
    corner = value.strip().lower()
    if corner not in CROP_CORNERS:
        choices = ", ".join(sorted(CROP_CORNERS))
        raise ParseError(f"corner must be one of: {choices}")
    return corner


def parse_speed_percent(value: str) -> float:
    """Parse speed: 80, 80%, 120, or 120% (percent of normal playback)."""
    s = value.strip().lower()
    if not s:
        raise ParseError("speed cannot be empty")
    if s.endswith("%"):
        percent = float(s[:-1])
    else:
        percent = float(s)
    if percent <= 0:
        raise ParseError("speed must be positive")
    return percent


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_looped{input_path.suffix}")


def default_crop_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_cropped{input_path.suffix}")


def format_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if h:
        return f"{h}h {m}m {s:.1f}s"
    return f"{m}m {s:.1f}s"
