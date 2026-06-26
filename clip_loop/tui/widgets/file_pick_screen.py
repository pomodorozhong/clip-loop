"""File picker modal screen."""

from __future__ import annotations

from pathlib import Path

from textual import on
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree


class FilePickScreen(ModalScreen[Path | None]):
    """Pick a file from the filesystem."""

    BINDINGS = [("escape", "dismiss", "Cancel")]

    DEFAULT_CSS = """
    FilePickScreen DirectoryTree {
        height: 1fr;
    }
    .pick-actions {
        height: auto;
        padding: 1;
        align: center middle;
    }
    """

    def __init__(self, start: Path | None = None) -> None:
        super().__init__()
        self._start = start or Path.cwd()

    def compose(self):
        yield DirectoryTree(str(self._start))
        yield Horizontal(
            Button("Select", variant="primary", id="pick-select"),
            Button("Cancel", id="pick-cancel"),
            classes="pick-actions",
        )

    def _selected_path(self) -> Path | None:
        tree = self.query_one(DirectoryTree)
        node = tree.cursor_node
        if node is None or node.data is None:
            return None
        path = node.data.path
        return path if path.is_file() else None

    @on(Button.Pressed, "#pick-select")
    def select_pressed(self) -> None:
        path = self._selected_path()
        if path is not None:
            self.dismiss(path)

    @on(Button.Pressed, "#pick-cancel")
    def cancel_pressed(self) -> None:
        self.dismiss(None)

    @on(DirectoryTree.FileSelected)
    def file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.dismiss(Path(event.path))
