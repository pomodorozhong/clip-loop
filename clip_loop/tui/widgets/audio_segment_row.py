"""Audio segment row widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Button, Checkbox, Input, Select

from clip_loop.tui.constants import MS_PRESETS
from clip_loop.tui.widgets.collapsible_segment_row import CollapsibleSegmentRow
from clip_loop.tui.widgets.field_label import FieldLabel
from clip_loop.tui.widgets.field_row import FieldRow
from clip_loop.tui.widgets.preset_input import PresetInput


class AudioSegmentRow(CollapsibleSegmentRow):
    """One audio segment row in the Multiple tab."""

    ROW_PREFIX = "audio-seg"
    TITLE_PREFIX = "Audio"

    DEFAULT_CSS = """
    AudioSegmentRow Select {
        width: 1fr;
    }
    """

    def _content(self) -> ComposeResult:
        prefix = f"{self.ROW_PREFIX}-{self.index}"
        with FieldRow():
            yield Input(placeholder="path/to/audio.mp3", id=f"{prefix}-path")
            yield Button("Browse…", id=f"{prefix}-browse")
        yield FieldLabel("Trim start")
        yield Select(MS_PRESETS, id=f"{prefix}-trim-preset", value="0")
        yield PresetInput(
            placeholder="milliseconds",
            id=f"{prefix}-trim-custom",
        )
        yield Checkbox("Ping-pong audio", id=f"{prefix}-alternate-reverse")
