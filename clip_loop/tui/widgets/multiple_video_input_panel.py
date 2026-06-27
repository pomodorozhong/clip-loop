"""Multiple video segments list panel."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button

from clip_loop.tui.widgets.segment_add_row import SegmentAddRow


class MultipleVideoInputPanel(Vertical):
    """Dynamic video segment list with add button."""

    DEFAULT_CSS = """
    MultipleVideoInputPanel {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Vertical(id="video-segments-list")
        with SegmentAddRow():
            yield Button("Add video", id="add-video-segment")
