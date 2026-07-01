"""Tests for clip_loop.tui.constants.field_mapping."""

from __future__ import annotations

from clip_loop.tui.constants.field_mapping import widget_for_field


def test_widget_for_field_none() -> None:
    assert widget_for_field(None, video_multiple=False, audio_multiple=False) == "#input-path"


def test_widget_for_field_duration_custom() -> None:
    assert (
        widget_for_field(
            "duration",
            video_multiple=False,
            audio_multiple=False,
            duration_is_custom=True,
        )
        == "#duration-custom"
    )


def test_widget_for_field_single_mode() -> None:
    assert (
        widget_for_field(
            "video_segments[0].path",
            video_multiple=False,
            audio_multiple=False,
        )
        == "#input-path"
    )


def test_widget_for_field_video_multiple() -> None:
    assert (
        widget_for_field(
            "video_segments[1].speed_percent",
            video_multiple=True,
            audio_multiple=False,
        )
        == "#video-seg-1-speed-preset"
    )


def test_widget_for_field_audio_multiple() -> None:
    assert (
        widget_for_field(
            "audio_segments[0].trim_start_ms",
            video_multiple=False,
            audio_multiple=True,
        )
        == "#audio-seg-0-trim-preset"
    )


def test_widget_for_field_video_segments_list() -> None:
    assert (
        widget_for_field(
            "video_segments",
            video_multiple=True,
            audio_multiple=False,
        )
        == "#video-segments-list"
    )
