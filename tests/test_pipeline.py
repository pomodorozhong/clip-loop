"""Tests for clip_loop.pipeline."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from clip_loop.media import ffprobe_video_size
from clip_loop.options import AudioSegment, ClipLoopOptions, VideoSegment
from clip_loop.pipeline import export_preview_video_clips, run_clip_loop


def _video_duration_sec(path: Path) -> float:
    import subprocess

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def test_run_clip_loop_single_video(tmp_media_dir: Path, tmp_path: Path) -> None:
    video = tmp_media_dir / "sample.mp4"
    output = tmp_path / "out.mp4"
    options = ClipLoopOptions(
        video_segments=(VideoSegment(path=video),),
        duration=3.0,
        output_path=output,
    )
    result = run_clip_loop(options)
    assert result == output
    assert output.is_file()
    duration = _video_duration_sec(output)
    assert 2.5 <= duration <= 3.5


def test_run_clip_loop_with_external_audio(
    tmp_media_dir: Path, tmp_path: Path
) -> None:
    video = tmp_media_dir / "sample.mp4"
    audio = tmp_media_dir / "sample.m4a"
    output = tmp_path / "with_audio.mp4"
    options = ClipLoopOptions(
        video_segments=(VideoSegment(path=video),),
        duration=3.0,
        output_path=output,
        audio_segments=(AudioSegment(path=audio),),
    )
    result = run_clip_loop(options)
    assert result == output
    assert output.is_file()


def test_run_clip_loop_multi_segment_join(
    tmp_media_dir: Path, tmp_path: Path
) -> None:
    video = tmp_media_dir / "sample.mp4"
    clip_a = tmp_path / "a.mp4"
    clip_b = tmp_path / "b.mp4"
    shutil.copy(video, clip_a)
    shutil.copy(video, clip_b)
    output = tmp_path / "joined.mp4"
    options = ClipLoopOptions(
        video_segments=(
            VideoSegment(path=clip_a),
            VideoSegment(path=clip_b),
        ),
        duration=4.0,
        output_path=output,
    )
    result = run_clip_loop(options)
    assert result == output
    assert output.is_file()
    duration = _video_duration_sec(output)
    assert 3.5 <= duration <= 4.5


def test_export_preview_video_clips(tmp_media_dir: Path, tmp_path: Path) -> None:
    video = tmp_media_dir / "sample.mp4"
    clip_a = tmp_path / "a.mp4"
    clip_b = tmp_path / "b.mp4"
    shutil.copy(video, clip_a)
    shutil.copy(video, clip_b)
    output = tmp_path / "joined.mp4"
    options = ClipLoopOptions(
        video_segments=(
            VideoSegment(path=clip_a, speed_percent=80.0),
            VideoSegment(path=clip_b, trim_start_ms=200),
        ),
        duration=4.0,
        output_path=output,
    )

    preview_dir, preview_files = export_preview_video_clips(options)
    assert preview_dir == tmp_path / "preview"
    assert len(preview_files) == 2
    assert all(path.is_file() for path in preview_files)
