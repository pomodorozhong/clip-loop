"""Shared pytest fixtures and TUI widget stubs."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from clip_loop._test_fixtures import FIXTURES_DIR, FIXTURE_SPECS, generate_fixtures
from clip_loop.ffmpeg import ensure_ffmpeg
from clip_loop.options import AudioSegment, ClipLoopOptions, VideoSegment


class _Blank:
    """Sentinel matching Textual Select.BLANK."""


BLANK = _Blank()


@dataclass
class FakeInput:
    value: str = ""
    display: bool = True
    disabled: bool = False


@dataclass
class FakeSelect:
    value: str | _Blank = field(default_factory=lambda: BLANK)


@dataclass
class FakeCheckbox:
    value: bool = False
    disabled: bool = False


@dataclass
class FakeTabbedContent:
    active: str = ""


class FakeWidgetHost:
    """Minimal query_one host for TUI field/segment tests."""

    def __init__(self, widgets: dict[str, object] | None = None) -> None:
        self.widgets = widgets or {}

    def query_one(self, selector: str, expect_type: type | None = None):
        key = selector.lstrip("#")
        if key not in self.widgets:
            raise KeyError(f"Unknown widget: {selector}")
        widget = self.widgets[key]
        if expect_type is not None and not isinstance(widget, expect_type):
            # Allow Fake* stubs when expect_type is Textual widget class.
            return widget
        return widget


def make_options(
    video_path: Path,
    *,
    duration: float = 5.0,
    output_path: Path | None = None,
    audio_path: Path | None = None,
    **kwargs,
) -> ClipLoopOptions:
    video = VideoSegment(path=video_path, **kwargs.get("video_kwargs", {}))
    audio_segments: tuple[AudioSegment, ...] = ()
    if audio_path is not None:
        audio_segments = (AudioSegment(path=audio_path),)
    return ClipLoopOptions(
        video_segments=(video,),
        duration=duration,
        output_path=output_path,
        audio_segments=audio_segments,
        audio_crossfade_ms=kwargs.get("audio_crossfade_ms", 0),
        audio_gap_ms=kwargs.get("audio_gap_ms", 0),
        audio_seam_fade_ms=kwargs.get("audio_seam_fade_ms", 0),
        target_resolution=kwargs.get("target_resolution"),
        fill_mode=kwargs.get("fill_mode", "fit"),
    )


def _ensure_fixture_files() -> None:
    missing = [FIXTURES_DIR / name for name in FIXTURE_SPECS if not (FIXTURES_DIR / name).is_file()]
    if missing:
        generate_fixtures()


@pytest.fixture(scope="session")
def ffmpeg_available() -> None:
    ensure_ffmpeg()


@pytest.fixture(scope="session")
def sample_video(ffmpeg_available: None) -> Path:
    _ensure_fixture_files()
    path = FIXTURES_DIR / "sample.mp4"
    assert path.is_file(), f"Missing fixture: {path}"
    return path


@pytest.fixture(scope="session")
def sample_audio(ffmpeg_available: None) -> Path:
    _ensure_fixture_files()
    path = FIXTURES_DIR / "sample.m4a"
    assert path.is_file(), f"Missing fixture: {path}"
    return path


@pytest.fixture(scope="session")
def sample_video_noaudio(ffmpeg_available: None) -> Path:
    _ensure_fixture_files()
    path = FIXTURES_DIR / "sample_noaudio.mp4"
    assert path.is_file(), f"Missing fixture: {path}"
    return path


@pytest.fixture
def tmp_media_dir(
    sample_video: Path,
    sample_audio: Path,
    sample_video_noaudio: Path,
    tmp_path: Path,
) -> Path:
    media = tmp_path / "media"
    media.mkdir()
    shutil.copy(sample_video, media / "sample.mp4")
    shutil.copy(sample_audio, media / "sample.m4a")
    shutil.copy(sample_video_noaudio, media / "sample_noaudio.mp4")
    return media
