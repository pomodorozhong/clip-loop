"""Optional output file path field."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical

from clip_loop.tui.widgets.field_label import FieldLabel
from clip_loop.tui.widgets.path_browse_row import PathBrowseRow


class OutputPathFields(Vertical):
    """Output path input with browse button."""

    DEFAULT_CSS = """
    OutputPathFields {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield FieldLabel("Output file (optional)")
        yield PathBrowseRow(
            input_id="output-path",
            browse_id="browse-output",
            placeholder="default: <stem>_looped<suffix>",
        )
