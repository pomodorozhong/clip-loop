"""Tests for clip_loop.tui.form."""

from __future__ import annotations

from pathlib import Path

from clip_loop.tui.form import ClipLoopForm
from tests.conftest import FakeCheckbox, FakeInput, FakeSelect, FakeTabbedContent, FakeWidgetHost


def _single_mode_host(video_path: Path) -> FakeWidgetHost:
    return FakeWidgetHost(
        {
            "video-input-tabs": FakeTabbedContent(active="video-single-tab"),
            "audio-input-tabs": FakeTabbedContent(active="audio-single-tab"),
            "input-path": FakeInput(value=str(video_path)),
            "output-path": FakeInput(value=""),
            "duration-preset": FakeSelect(value="30s"),
            "duration-custom": FakeInput(),
            "trim-preset": FakeSelect(value="0"),
            "trim-custom": FakeInput(),
            "speed-preset": FakeSelect(value="100"),
            "speed-custom": FakeInput(),
            "keep-ratio-preset": FakeSelect(value="off"),
            "keep-ratio-custom": FakeInput(),
            "crop-corner": FakeSelect(value="top_left"),
            "alternate-reverse": FakeCheckbox(value=False),
            "audio-path": FakeInput(value=""),
            "audio-trim-preset": FakeSelect(value="0"),
            "audio-trim-custom": FakeInput(),
            "audio-alternate-reverse": FakeCheckbox(value=False),
            "crossfade-preset": FakeSelect(value="0"),
            "crossfade-custom": FakeInput(),
            "gap-preset": FakeSelect(value="0"),
            "gap-custom": FakeInput(),
            "seam-fade-preset": FakeSelect(value="0"),
            "seam-fade-custom": FakeInput(),
            "resolution-preset": FakeSelect(value="source"),
            "resolution-custom": FakeInput(),
            "fill-mode": FakeSelect(value="fit"),
            "video-segments-list": FakeWidgetHost({}),
            "audio-segments-list": FakeWidgetHost({}),
        }
    )


def test_clip_loop_form_collect_single_mode(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")
    host = _single_mode_host(video)
    form = ClipLoopForm(host)  # type: ignore[arg-type]
    options = form.collect()
    assert options.input_path == video
    assert options.duration == 30.0
    assert options.output_path is None
    assert len(options.video_segments) == 1
    assert options.audio_segments == ()


def test_clip_loop_form_duration_is_custom() -> None:
    host = FakeWidgetHost(
        {
            "duration-preset": FakeSelect(value="custom"),
        }
    )
    form = ClipLoopForm(host)  # type: ignore[arg-type]
    assert form.duration_is_custom() is True
