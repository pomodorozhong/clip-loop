"""Compose the clip-loop TUI form layout."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Checkbox, Input, Select, TabbedContent, TabPane

from clip_loop.tui.constants import (
    CROP_CORNER_PRESETS,
    DURATION_PRESETS,
    KEEP_RATIO_PRESETS,
    MS_PRESETS,
    SPEED_PRESETS,
)
from clip_loop.tui.widgets import (
    FieldLabel,
    FieldRow,
    FormGroupBody,
    FormGroupBox,
    FormGroupTitle,
    PresetInput,
    SegmentAddRow,
)


def compose_form() -> ComposeResult:
    """Yield the main configuration form widgets."""
    yield FieldLabel("Target duration")
    yield Select(DURATION_PRESETS, id="duration-preset", value="1h")
    yield PresetInput(
        placeholder="e.g. 45m or 3600",
        id="duration-custom",
    )

    yield FieldLabel("Output file (optional)")
    with FieldRow():
        yield Input(
            placeholder="default: <stem>_looped<suffix>",
            id="output-path",
        )
        yield Button("Browse…", id="browse-output")

    with TabbedContent(id="media-options-tabs"):
        with TabPane("Video", id="media-video-tab"):
            with FormGroupBox():
                yield FormGroupTitle("Video input")
                with FormGroupBody():
                    with TabbedContent(id="video-input-tabs"):
                        with TabPane("Single", id="video-single-tab"):
                            with FieldRow():
                                yield Input(
                                    placeholder="path/to/clip.mp4",
                                    id="input-path",
                                )
                                yield Button("Browse…", id="browse-input")
                            yield FieldLabel("Trim start")
                            yield Select(MS_PRESETS, id="trim-preset", value="0")
                            yield PresetInput(
                                placeholder="milliseconds",
                                id="trim-custom",
                            )
                            yield FieldLabel("Playback speed")
                            yield Select(SPEED_PRESETS, id="speed-preset", value="100")
                            yield PresetInput(
                                placeholder="e.g. 80 or 120",
                                id="speed-custom",
                            )
                            yield FieldLabel("Crop before loop")
                            yield Select(
                                KEEP_RATIO_PRESETS,
                                id="keep-ratio-preset",
                                value="off",
                            )
                            yield PresetInput(
                                placeholder="e.g. 75% or 0.75",
                                id="keep-ratio-custom",
                                disabled=True,
                            )
                            yield FieldLabel("Crop corner")
                            yield Select(
                                CROP_CORNER_PRESETS,
                                id="crop-corner",
                                value="top_left",
                                disabled=True,
                            )
                            yield Checkbox(
                                "Ping-pong video (--alternate-reverse)",
                                id="alternate-reverse",
                            )
                        with TabPane("Multiple", id="video-multiple-tab"):
                            yield Vertical(id="video-segments-list")
                            with SegmentAddRow():
                                yield Button(
                                    "Add video",
                                    id="add-video-segment",
                                )

        with TabPane("Audio", id="media-audio-tab"):
            yield FieldLabel("Crossfade at loop seams")
            yield Select(
                MS_PRESETS,
                id="crossfade-preset",
                value="0",
                disabled=True,
            )
            yield PresetInput(
                placeholder="milliseconds",
                id="crossfade-custom",
                disabled=True,
            )
            yield FieldLabel("Silence gap between loops")
            yield Select(MS_PRESETS, id="gap-preset", value="0", disabled=True)
            yield PresetInput(
                placeholder="milliseconds",
                id="gap-custom",
                disabled=True,
            )
            yield FieldLabel("Seam fade in/out")
            yield Select(
                MS_PRESETS,
                id="seam-fade-preset",
                value="0",
                disabled=True,
            )
            yield PresetInput(
                placeholder="milliseconds",
                id="seam-fade-custom",
                disabled=True,
            )

            with FormGroupBox():
                yield FormGroupTitle("Audio input")
                with FormGroupBody():
                    with TabbedContent(id="audio-input-tabs"):
                        with TabPane("Single", id="audio-single-tab"):
                            yield FieldLabel("External audio (optional)")
                            with FieldRow():
                                yield Input(
                                    placeholder="path/to/audio.mp3",
                                    id="audio-path",
                                )
                                yield Button("Browse…", id="browse-audio")
                            yield FieldLabel("Trim start")
                            yield Select(
                                MS_PRESETS,
                                id="audio-trim-preset",
                                value="0",
                                disabled=True,
                            )
                            yield PresetInput(
                                placeholder="milliseconds",
                                id="audio-trim-custom",
                                disabled=True,
                            )
                            yield Checkbox(
                                "Ping-pong audio (--audio-alternate-reverse)",
                                id="audio-alternate-reverse",
                                disabled=True,
                            )
                        with TabPane("Multiple", id="audio-multiple-tab"):
                            yield Vertical(id="audio-segments-list")
                            with SegmentAddRow():
                                yield Button(
                                    "Add audio",
                                    id="add-audio-segment",
                                )
