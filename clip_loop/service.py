"""Orchestrate validation, preprocessing, and looping."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from clip_loop.exceptions import ClipLoopError, FfmpegError
from clip_loop.ffmpeg import (
    AudioCycleBuilder,
    FfmpegMediaProbe,
    LoopEngine,
    SubprocessFfmpegExecutor,
    VideoProcessor,
    ensure_ffmpeg_available,
)
from clip_loop.models import AudioEffectOptions, ClipLoopOptions
from clip_loop.parsing import default_output_path
from clip_loop.validation import validate_clip_loop_options


class ClipLoopService:
    """Application service: validate options and produce a looped video."""

    def __init__(
        self,
        *,
        probe: FfmpegMediaProbe | None = None,
        executor: SubprocessFfmpegExecutor | None = None,
    ) -> None:
        self._probe = probe or FfmpegMediaProbe()
        executor = executor or SubprocessFfmpegExecutor()
        video = VideoProcessor(executor, self._probe)
        audio = AudioCycleBuilder(executor, self._probe)
        self._video = video
        self._engine = LoopEngine(video, audio)

    def run(self, options: ClipLoopOptions) -> Path:
        validate_clip_loop_options(options, self._probe)
        try:
            ensure_ffmpeg_available()
        except RuntimeError as exc:
            raise FfmpegError(str(exc)) from exc

        resolved_output = (
            options.output_path
            if options.output_path
            else default_output_path(options.input_path)
        )
        source_path = options.input_path
        temp_crop_path: Path | None = None
        temp_speed_path: Path | None = None
        loop_trim_start_sec = options.trim_start_sec
        audio_effects = AudioEffectOptions(
            alternate_reverse=options.audio_alternate_reverse,
            gap_sec=options.audio_gap_sec,
            crossfade_sec=options.audio_crossfade_sec,
            seam_fade_sec=options.audio_seam_fade_sec,
        )

        try:
            if options.keep_ratio is not None and options.crop_corner is not None:
                temp_crop_path = _make_temp(
                    suffix=options.input_path.suffix or ".mp4",
                    prefix="clip_loop_crop_",
                )
                self._video.crop(
                    input_path=options.input_path,
                    keep_ratio=options.keep_ratio,
                    corner=options.crop_corner,
                    output_path=temp_crop_path,
                )
                source_path = temp_crop_path

            if options.speed_percent != 100.0:
                temp_speed_path = _make_temp(
                    suffix=source_path.suffix or ".mp4",
                    prefix="clip_loop_speed_",
                )
                self._video.adjust_speed(
                    source_path,
                    temp_speed_path,
                    options.speed_percent,
                    trim_start_sec=loop_trim_start_sec,
                )
                source_path = temp_speed_path
                loop_trim_start_sec = 0.0

            if options.alternate_reverse:
                self._engine.loop_alternate_reverse(
                    source_path,
                    resolved_output,
                    options.duration,
                    trim_start_sec=loop_trim_start_sec,
                    external_audio_path=options.audio_path,
                    audio_effects=audio_effects,
                )
            else:
                self._engine.loop_simple(
                    source_path,
                    resolved_output,
                    options.duration,
                    trim_start_sec=loop_trim_start_sec,
                    external_audio_path=options.audio_path,
                    audio_effects=audio_effects,
                )
        except RuntimeError as exc:
            raise FfmpegError(str(exc)) from exc
        finally:
            if temp_speed_path is not None:
                temp_speed_path.unlink(missing_ok=True)
            if temp_crop_path is not None:
                temp_crop_path.unlink(missing_ok=True)

        return resolved_output


def _make_temp(*, suffix: str, prefix: str) -> Path:
    fd, tmp_name = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    os.close(fd)
    return Path(tmp_name)


def run_clip_loop(**kwargs) -> Path:
    """Backward-compatible entry point for the loop pipeline."""
    options = ClipLoopOptions(**kwargs)
    return ClipLoopService().run(options)
