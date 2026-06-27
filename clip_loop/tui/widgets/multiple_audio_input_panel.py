"""Multiple audio segments list panel."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button

from clip_loop.tui.widgets.segment_add_row import SegmentAddRow


class MultipleAudioInputPanel(Vertical):
    """Dynamic audio segment list with add button."""

    DEFAULT_CSS = """
    MultipleAudioInputPanel {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Vertical(id="audio-segments-list")
        with SegmentAddRow():
            yield Button("Add audio", id="add-audio-segment")
