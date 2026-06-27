"""Path input with browse button."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Button, Input

from clip_loop.tui.widgets.field_row import FieldRow


class PathBrowseRow(FieldRow):
    """Path input plus browse button."""

    def __init__(
        self,
        *,
        input_id: str,
        browse_id: str,
        placeholder: str,
    ) -> None:
        super().__init__()
        self._input_id = input_id
        self._browse_id = browse_id
        self._placeholder = placeholder

    def compose(self) -> ComposeResult:
        yield Input(placeholder=self._placeholder, id=self._input_id)
        yield Button("Browse…", id=self._browse_id)
