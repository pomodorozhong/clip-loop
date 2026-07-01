"""High-level clip-loop processing orchestration."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from clip_loop.errors import ClipLoopError
from clip_loop.ffmpeg import (
    apply_external_audio,
    cleanup_temp_paths,
    concat_audio_files,
    concat_video_files,
    default_output_path,
    unique_output_path,
    prepare_audio_source,
    preprocess_audio_segment,
    preprocess_video_segment,
    run_simple_loop,
    scale_video_to_target,
)
from clip_loop.options import ClipLoopOptions
from clip_loop.validation import validate_clip_loop_options


def loop_video_with_optional_audio(
    input_path: Path,
    output_path: Path,
    duration_sec: float,
    *,
    external_audio_path: Path | None = None,
    audio_crossfade_sec: float = 0.0,
    audio_gap_sec: float = 0.0,
    audio_seam_fade_sec: float = 0.0,
) -> None:
    """Build looped video, optionally replacing audio from an external file."""
    if external_audio_path is None:
        run_simple_loop(input_path, output_path, duration_sec)
        return

    fd, tmp_name = tempfile.mkstemp(suffix=output_path.suffix or ".mp4", prefix="clip_loop_")
    os.close(fd)
    temp_video_path = Path(tmp_name)
    audio_temp_paths: list[Path] = []
    try:
        run_simple_loop(input_path, temp_video_path, duration_sec)
        audio_source_path, audio_temp_paths = prepare_audio_source(
            external_audio_path,
            audio_crossfade_sec=audio_crossfade_sec,
            audio_gap_sec=audio_gap_sec,
            audio_seam_fade_sec=audio_seam_fade_sec,
        )
        apply_external_audio(temp_video_path, output_path, audio_source_path, duration_sec)
    except (subprocess.CalledProcessError, ValueError) as exc:
        raise ClipLoopError(
            "ffmpeg failed while applying external audio. "
            "Check that the audio file is a supported format."
        ) from exc
    finally:
        temp_video_path.unlink(missing_ok=True)
        cleanup_temp_paths(audio_temp_paths)


def _preprocess_video_segments(options: ClipLoopOptions) -> tuple[list[Path], list[Path]]:
    """Return processed per-segment videos and temp paths."""
    temps: list[Path] = []
    video_suffix = options.video_segments[0].path.suffix or ".mp4"
    processed_videos: list[Path] = []
    for segment in options.video_segments:
        path, segment_temps = preprocess_video_segment(segment)
        temps.extend(segment_temps)
        if options.target_resolution is not None:
            path, scale_temps = scale_video_to_target(
                path,
                target_resolution=options.target_resolution,
                fill_mode=options.fill_mode,
                suffix=video_suffix,
            )
            temps.extend(scale_temps)
        processed_videos.append(path)
    return processed_videos, temps


def _resolve_sources(options: ClipLoopOptions) -> tuple[Path, Path | None, list[Path]]:
    """Preprocess and join segments; return source video, external audio, and temps."""
    video_suffix = options.video_segments[0].path.suffix or ".mp4"
    processed_videos, temps = _preprocess_video_segments(options)

    if len(processed_videos) == 1:
        source_video = processed_videos[0]
    else:
        fd, tmp_name = tempfile.mkstemp(
            suffix=video_suffix,
            prefix="clip_loop_joined_",
        )
        os.close(fd)
        joined_video = Path(tmp_name)
        temps.append(joined_video)
        concat_video_files(
            processed_videos,
            joined_video,
            uniform_size=options.target_resolution,
        )
        source_video = joined_video

    external_audio: Path | None = None
    if options.audio_segments:
        processed_audio: list[Path] = []
        for segment in options.audio_segments:
            path, segment_temps = preprocess_audio_segment(segment)
            processed_audio.append(path)
            temps.extend(segment_temps)

        if len(processed_audio) == 1:
            external_audio = processed_audio[0]
        else:
            fd, tmp_name = tempfile.mkstemp(suffix=".m4a", prefix="clip_loop_joined_audio_")
            os.close(fd)
            joined_audio = Path(tmp_name)
            temps.append(joined_audio)
            concat_audio_files(processed_audio, joined_audio)
            external_audio = joined_audio

    return source_video, external_audio, temps


def export_preview_video_clips(
    options: ClipLoopOptions,
    *,
    base_output_path: Path | None = None,
) -> tuple[Path, list[Path]]:
    """Export post-processed per-segment clips into a preview folder."""
    validate_clip_loop_options(options)

    preview_target = base_output_path or options.preview_output_path or options.output_path
    if preview_target is None:
        preview_target = default_output_path(options.input_path)

    preview_parent = preview_target if preview_target.suffix == "" else preview_target.parent
    preview_dir = preview_parent / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)

    preprocess_temps: list[Path] = []
    output_paths: list[Path] = []
    try:
        processed_videos, preprocess_temps = _preprocess_video_segments(options)
        for index, processed in enumerate(processed_videos, start=1):
            suffix = processed.suffix or options.video_segments[index - 1].path.suffix or ".mp4"
            name = f"{index:02d}_{options.video_segments[index - 1].path.stem}{suffix}"
            destination = preview_dir / name
            shutil.copy2(processed, destination)
            output_paths.append(destination)
    except subprocess.CalledProcessError as exc:
        raise ClipLoopError("ffmpeg failed while creating preview clips.") from exc
    finally:
        cleanup_temp_paths(preprocess_temps)

    return preview_dir, output_paths


def run_clip_loop(options: ClipLoopOptions | None = None, /, **kwargs) -> Path:
    """Validate options, run ffmpeg, and return the output path."""
    if options is None:
        if "video_segments" in kwargs:
            options = ClipLoopOptions(**kwargs)
        else:
            options = ClipLoopOptions.from_legacy(**kwargs)
    elif kwargs:
        raise TypeError("pass either ClipLoopOptions or keyword arguments, not both")

    validate_clip_loop_options(options)

    audio_crossfade_sec = options.audio_crossfade_ms / 1000.0
    audio_gap_sec = options.audio_gap_ms / 1000.0
    audio_seam_fade_sec = options.audio_seam_fade_ms / 1000.0
    resolved_output = unique_output_path(
        options.output_path
        if options.output_path
        else default_output_path(options.input_path)
    )

    preprocess_temps: list[Path] = []
    try:
        source_video, external_audio, preprocess_temps = _resolve_sources(options)
        loop_video_with_optional_audio(
            source_video,
            resolved_output,
            options.duration,
            external_audio_path=external_audio,
            audio_crossfade_sec=audio_crossfade_sec,
            audio_gap_sec=audio_gap_sec,
            audio_seam_fade_sec=audio_seam_fade_sec,
        )
    except subprocess.CalledProcessError as exc:
        raise ClipLoopError("ffmpeg failed while processing clips.") from exc
    finally:
        cleanup_temp_paths(preprocess_temps)

    return resolved_output
