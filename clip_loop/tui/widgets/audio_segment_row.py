"""Audio segment row widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Checkbox

from clip_loop.tui.widgets.collapsible_segment_row import CollapsibleSegmentRow
from clip_loop.tui.widgets.ms_preset_field import MsPresetField
from clip_loop.tui.widgets.path_browse_row import PathBrowseRow


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
        yield PathBrowseRow(
            input_id=f"{prefix}-path",
            browse_id=f"{prefix}-browse",
            placeholder="path/to/audio.mp3",
        )
        yield MsPresetField(
            "Trim start",
            f"{prefix}-trim-preset",
            f"{prefix}-trim-custom",
        )
        yield Checkbox("Ping-pong audio", id=f"{prefix}-alternate-reverse")
