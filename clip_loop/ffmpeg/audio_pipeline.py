"""Prepare external audio with optional effect chain."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from clip_loop.ffmpeg.audio import AudioCycleBuilder
from clip_loop.models import AudioEffectOptions


class ExternalAudioPipeline:
    """Apply audio effects in a fixed order, managing intermediate temp files."""

    def __init__(self, audio: AudioCycleBuilder) -> None:
        self._audio = audio

    def prepare_source(
        self, external_audio_path: Path, effects: AudioEffectOptions
    ) -> tuple[Path, list[Path]]:
        """Return processed audio path and temp files the caller must delete."""
        source_path = external_audio_path
        temp_paths: list[Path] = []

        if effects.alternate_reverse:
            temp_path = _make_temp(".m4a", temp_paths)
            self._audio.build_forward_reverse_cycle(external_audio_path, temp_path)
            source_path = temp_path

        if effects.gap_sec > 0:
            temp_path = _make_temp(".m4a", temp_paths)
            self._audio.build_gapped_cycle(source_path, temp_path, gap_sec=effects.gap_sec)
            source_path = temp_path

        if effects.crossfade_sec > 0:
            temp_path = _make_temp(".m4a", temp_paths)
            self._audio.build_crossfaded_cycle(
                source_path, temp_path, crossfade_sec=effects.crossfade_sec
            )
            source_path = temp_path

        if effects.seam_fade_sec > 0:
            temp_path = _make_temp(".m4a", temp_paths)
            self._audio.build_seam_faded_cycle(
                source_path, temp_path, fade_sec=effects.seam_fade_sec
            )
            source_path = temp_path

        return source_path, temp_paths


def _make_temp(suffix: str, temp_paths: list[Path]) -> Path:
    fd, tmp_name = tempfile.mkstemp(suffix=suffix, prefix="clip_loop_")
    os.close(fd)
    path = Path(tmp_name)
    temp_paths.append(path)
    return path


def cleanup_temp_paths(temp_paths: list[Path]) -> None:
    for path in temp_paths:
        path.unlink(missing_ok=True)
