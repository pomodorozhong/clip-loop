"""ffprobe-based media inspection."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol


class MediaProbe(Protocol):
    """Read metadata from media files without re-encoding."""

    def video_size(self, path: Path) -> tuple[int, int]: ...

    def has_audio(self, path: Path) -> bool: ...

    def audio_duration_sec(self, path: Path) -> float: ...


class FfmpegMediaProbe:
    """MediaProbe implementation backed by ffprobe."""

    def video_size(self, path: Path) -> tuple[int, int]:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        value = result.stdout.strip()
        if not value or "x" not in value:
            raise ValueError(f"ffprobe could not determine video size: {path}")
        width_str, height_str = value.split("x", 1)
        return int(width_str), int(height_str)

    def has_audio(self, path: Path) -> bool:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return bool(result.stdout.strip())

    def audio_duration_sec(self, path: Path) -> float:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        value = result.stdout.strip()
        if not value:
            raise ValueError(f"ffprobe could not determine audio duration: {path}")
        return float(value)
