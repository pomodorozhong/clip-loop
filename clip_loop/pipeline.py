"""High-level clip-loop processing orchestration."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from clip_loop.errors import ClipLoopError
from clip_loop.ffmpeg import (
    apply_external_audio,
    build_forward_reverse_cycle,
    cleanup_temp_paths,
    default_output_path,
    ensure_ffmpeg,
    ffprobe_has_audio,
    prepare_audio_source,
    run_crop_video,
    run_simple_loop,
    run_speed_adjust,
    run_stream_loop_copy,
)
from clip_loop.options import ClipLoopOptions
from clip_loop.validation import validate_clip_loop_options


def loop_video_with_optional_audio(
    input_path: Path,
    output_path: Path,
    duration_sec: float,
    *,
    trim_start_sec: float = 0.0,
    external_audio_path: Path | None = None,
    audio_alternate_reverse: bool = False,
    audio_crossfade_sec: float = 0.0,
    audio_gap_sec: float = 0.0,
    audio_seam_fade_sec: float = 0.0,
) -> None:
    """Build looped video, optionally replacing audio from an external file."""
    if external_audio_path is None:
        run_simple_loop(
            input_path, output_path, duration_sec, trim_start_sec=trim_start_sec
        )
        return

    fd, tmp_name = tempfile.mkstemp(suffix=output_path.suffix or ".mp4", prefix="clip_loop_")
    os.close(fd)
    temp_video_path = Path(tmp_name)
    audio_temp_paths: list[Path] = []
    try:
        run_simple_loop(
            input_path, temp_video_path, duration_sec, trim_start_sec=trim_start_sec
        )
        audio_source_path, audio_temp_paths = prepare_audio_source(
            external_audio_path,
            audio_alternate_reverse=audio_alternate_reverse,
            audio_crossfade_sec=audio_crossfade_sec,
            audio_gap_sec=audio_gap_sec,
            audio_seam_fade_sec=audio_seam_fade_sec,
        )
        apply_external_audio(temp_video_path, output_path, audio_source_path, duration_sec)
    except (subprocess.CalledProcessError, ValueError):
        sys.stderr.write(
            "ffmpeg failed while applying external audio. "
            "Check that the audio file is a supported format.\n"
        )
        sys.exit(1)
    finally:
        temp_video_path.unlink(missing_ok=True)
        cleanup_temp_paths(audio_temp_paths)


def run_alternate_reverse_loop(
    input_path: Path,
    output_path: Path,
    duration_sec: float,
    *,
    trim_start_sec: float = 0.0,
    external_audio_path: Path | None = None,
    audio_alternate_reverse: bool = False,
    audio_crossfade_sec: float = 0.0,
    audio_gap_sec: float = 0.0,
    audio_seam_fade_sec: float = 0.0,
) -> None:
    ensure_ffmpeg()
    has_audio = ffprobe_has_audio(input_path)
    fd, tmp_name = tempfile.mkstemp(suffix=".mp4", prefix="clip_loop_")
    os.close(fd)
    cycle_path = Path(tmp_name)
    try:
        try:
            build_forward_reverse_cycle(
                input_path,
                cycle_path,
                has_audio=has_audio,
                trim_start_sec=trim_start_sec,
            )
        except subprocess.CalledProcessError:
            sys.stderr.write(
                "ffmpeg failed while building forward/reverse cycle. "
                "Check that the file is a supported video (and audio) format.\n"
            )
            sys.exit(1)

        if external_audio_path is None:
            try:
                run_stream_loop_copy(cycle_path, output_path, duration_sec)
            except subprocess.CalledProcessError:
                sys.stderr.write(
                    "ffmpeg failed while looping the cycle to the target duration.\n"
                )
                sys.exit(1)
            return

        fd2, tmp_name2 = tempfile.mkstemp(
            suffix=output_path.suffix or ".mp4", prefix="clip_loop_"
        )
        os.close(fd2)
        temp_video_path = Path(tmp_name2)
        audio_temp_paths: list[Path] = []
        try:
            run_stream_loop_copy(cycle_path, temp_video_path, duration_sec)
            audio_source_path, audio_temp_paths = prepare_audio_source(
                external_audio_path,
                audio_alternate_reverse=audio_alternate_reverse,
                audio_crossfade_sec=audio_crossfade_sec,
                audio_gap_sec=audio_gap_sec,
                audio_seam_fade_sec=audio_seam_fade_sec,
            )
            apply_external_audio(
                temp_video_path, output_path, audio_source_path, duration_sec
            )
        except (subprocess.CalledProcessError, ValueError):
            sys.stderr.write(
                "ffmpeg failed while looping with external audio.\n"
            )
            sys.exit(1)
        finally:
            temp_video_path.unlink(missing_ok=True)
            cleanup_temp_paths(audio_temp_paths)
    finally:
        cycle_path.unlink(missing_ok=True)


def run_clip_loop(options: ClipLoopOptions | None = None, /, **kwargs) -> Path:
    """Validate options, run ffmpeg, and return the output path."""
    if options is None:
        options = ClipLoopOptions(**kwargs)
    elif kwargs:
        raise TypeError("pass either ClipLoopOptions or keyword arguments, not both")

    validate_clip_loop_options(options)

    trim_start_sec = options.trim_start_ms / 1000.0
    audio_crossfade_sec = options.audio_crossfade_ms / 1000.0
    audio_gap_sec = options.audio_gap_ms / 1000.0
    audio_seam_fade_sec = options.audio_seam_fade_ms / 1000.0
    resolved_output = (
        options.output_path if options.output_path else default_output_path(options.input_path)
    )
    source_path = options.input_path
    temp_crop_path: Path | None = None
    temp_speed_path: Path | None = None
    loop_trim_start_sec = trim_start_sec
    try:
        if options.keep_ratio is not None and options.crop_corner is not None:
            fd, tmp_name = tempfile.mkstemp(
                suffix=options.input_path.suffix or ".mp4", prefix="clip_loop_crop_"
            )
            os.close(fd)
            temp_crop_path = Path(tmp_name)
            run_crop_video(
                input_path=options.input_path,
                keep_ratio=options.keep_ratio,
                corner=options.crop_corner,
                output_path=temp_crop_path,
            )
            source_path = temp_crop_path
        if options.speed_percent != 100.0:
            fd, tmp_name = tempfile.mkstemp(
                suffix=source_path.suffix or ".mp4", prefix="clip_loop_speed_"
            )
            os.close(fd)
            temp_speed_path = Path(tmp_name)
            run_speed_adjust(
                source_path,
                temp_speed_path,
                options.speed_percent,
                trim_start_sec=loop_trim_start_sec,
            )
            source_path = temp_speed_path
            loop_trim_start_sec = 0.0
        if options.alternate_reverse:
            run_alternate_reverse_loop(
                source_path,
                resolved_output,
                options.duration,
                trim_start_sec=loop_trim_start_sec,
                external_audio_path=options.audio_path,
                audio_alternate_reverse=options.audio_alternate_reverse,
                audio_crossfade_sec=audio_crossfade_sec,
                audio_gap_sec=audio_gap_sec,
                audio_seam_fade_sec=audio_seam_fade_sec,
            )
        else:
            loop_video_with_optional_audio(
                source_path,
                resolved_output,
                options.duration,
                trim_start_sec=loop_trim_start_sec,
                external_audio_path=options.audio_path,
                audio_alternate_reverse=options.audio_alternate_reverse,
                audio_crossfade_sec=audio_crossfade_sec,
                audio_gap_sec=audio_gap_sec,
                audio_seam_fade_sec=audio_seam_fade_sec,
            )
    finally:
        if temp_speed_path is not None:
            temp_speed_path.unlink(missing_ok=True)
        if temp_crop_path is not None:
            temp_crop_path.unlink(missing_ok=True)
    return resolved_output
