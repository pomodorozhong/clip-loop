"""Video segment row widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Button, Checkbox, Input, Select

from clip_loop.tui.constants import (
    CROP_CORNER_PRESETS,
    KEEP_RATIO_PRESETS,
    MS_PRESETS,
    SPEED_PRESETS,
)
from clip_loop.tui.widgets.collapsible_segment_row import CollapsibleSegmentRow
from clip_loop.tui.widgets.field_label import FieldLabel
from clip_loop.tui.widgets.field_row import FieldRow
from clip_loop.tui.widgets.preset_input import PresetInput


class VideoSegmentRow(CollapsibleSegmentRow):
    """One video segment row in the Multiple tab."""

    ROW_PREFIX = "video-seg"
    TITLE_PREFIX = "Video"

    DEFAULT_CSS = """
    VideoSegmentRow Select {
        width: 1fr;
    }
    """

    def _content(self) -> ComposeResult:
        prefix = f"{self.ROW_PREFIX}-{self.index}"
        with FieldRow():
            yield Input(placeholder="path/to/clip.mp4", id=f"{prefix}-path")
            yield Button("Browse…", id=f"{prefix}-browse")
        yield FieldLabel("Trim start")
        yield Select(MS_PRESETS, id=f"{prefix}-trim-preset", value="0")
        yield PresetInput(
            placeholder="milliseconds",
            id=f"{prefix}-trim-custom",
        )
        yield FieldLabel("Playback speed")
        yield Select(SPEED_PRESETS, id=f"{prefix}-speed-preset", value="100")
        yield PresetInput(
            placeholder="e.g. 80 or 120",
            id=f"{prefix}-speed-custom",
        )
        yield FieldLabel("Crop before loop")
        yield Select(KEEP_RATIO_PRESETS, id=f"{prefix}-keep-ratio-preset", value="off")
        yield PresetInput(
            placeholder="e.g. 75% or 0.75",
            id=f"{prefix}-keep-ratio-custom",
            disabled=True,
        )
        yield FieldLabel("Crop corner")
        yield Select(
            CROP_CORNER_PRESETS,
            id=f"{prefix}-crop-corner",
            value="top_left",
            disabled=True,
        )
        yield Checkbox("Ping-pong video", id=f"{prefix}-alternate-reverse")
