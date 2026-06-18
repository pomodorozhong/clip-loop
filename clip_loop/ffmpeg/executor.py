"""ffmpeg/ffprobe subprocess execution."""

from __future__ import annotations

import shutil
import subprocess
from typing import Protocol


class FfmpegExecutor(Protocol):
    """Run ffmpeg command lines (dependency inversion for tests and wrappers)."""

    def run(self, cmd: list[str], *, error_message: str) -> None: ...


class SubprocessFfmpegExecutor:
    """Default executor that invokes ffmpeg via subprocess."""

    def run(self, cmd: list[str], *, error_message: str) -> None:
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(error_message) from exc


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "clip-loop requires ffmpeg in PATH. Install it from https://ffmpeg.org/"
        )
