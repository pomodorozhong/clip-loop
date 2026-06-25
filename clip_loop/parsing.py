"""Argument and option string parsers."""

from __future__ import annotations

import argparse

CROP_CORNERS = frozenset({"top_left", "top_right", "bottom_left", "bottom_right"})
FILL_MODES = frozenset({"fit", "fill"})


def parse_duration(value: str) -> float:
    """Parse duration: plain number = seconds, or suffix h/m/s (e.g. 1h, 30m, 90s)."""
    s = value.strip().lower()
    if not s:
        raise argparse.ArgumentTypeError("duration cannot be empty")
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
        raise argparse.ArgumentTypeError("keep ratio cannot be empty")
    if s.endswith("%"):
        ratio = float(s[:-1]) / 100.0
    else:
        ratio = float(s)
        if ratio > 1.0:
            ratio /= 100.0
    if not 0.0 < ratio <= 1.0:
        raise argparse.ArgumentTypeError("keep ratio must be between 0 and 100%")
    return ratio


def parse_crop_corner(value: str) -> str:
    corner = value.strip().lower()
    if corner not in CROP_CORNERS:
        choices = ", ".join(sorted(CROP_CORNERS))
        raise argparse.ArgumentTypeError(f"corner must be one of: {choices}")
    return corner


def parse_speed_percent(value: str) -> float:
    """Parse speed: 80, 80%, 120, or 120% (percent of normal playback)."""
    s = value.strip().lower()
    if not s:
        raise argparse.ArgumentTypeError("speed cannot be empty")
    if s.endswith("%"):
        percent = float(s[:-1])
    else:
        percent = float(s)
    if percent <= 0:
        raise argparse.ArgumentTypeError("speed must be positive")
    return percent


def parse_resolution(value: str) -> tuple[int, int]:
    """Parse resolution: WIDTHxHEIGHT (e.g. 1920x1080). Dimensions are forced even."""
    s = value.strip().lower().replace(" ", "")
    if not s:
        raise argparse.ArgumentTypeError("resolution cannot be empty")
    if "x" not in s:
        raise argparse.ArgumentTypeError("resolution must be WIDTHxHEIGHT (e.g. 1920x1080)")
    width_str, height_str = s.split("x", 1)
    try:
        width = int(width_str)
        height = int(height_str)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "resolution must be WIDTHxHEIGHT with positive integers"
        ) from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("resolution width and height must be positive")
    return width & ~1, height & ~1


def parse_fill_mode(value: str) -> str:
    mode = value.strip().lower()
    if mode not in FILL_MODES:
        choices = ", ".join(sorted(FILL_MODES))
        raise argparse.ArgumentTypeError(f"fill mode must be one of: {choices}")
    return mode


def format_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if h:
        return f"{h}h {m}m {s:.1f}s"
    return f"{m}m {s:.1f}s"
