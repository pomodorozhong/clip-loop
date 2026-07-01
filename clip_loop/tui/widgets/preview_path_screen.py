"""Modal screen for entering a preview output path."""

from __future__ import annotations

from pathlib import Path

from textual import on
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class PreviewPathScreen(ModalScreen[Path | None]):
    """Prompt for a base path used to create the preview folder."""

    BINDINGS = [("escape", "dismiss", "Cancel")]

    DEFAULT_CSS = """
    PreviewPathScreen > Vertical {
        width: 70;
        height: auto;
        padding: 1 2;
        background: $panel;
        border: round $accent;
    }
    PreviewPathScreen Input {
        margin-top: 1;
        margin-bottom: 1;
    }
    .preview-actions {
        height: auto;
        align: right middle;
    }
    .preview-title {
        text-style: bold;
    }
    """

    def __init__(self, default_path: Path) -> None:
        super().__init__()
        self._default_path = default_path

    def compose(self):
        with Vertical():
            yield Label("Preview video clips", classes="preview-title")
            yield Label("Output path (preview folder will be created here):")
            yield Input(value=str(self._default_path), id="preview-path-input")
            yield Horizontal(
                Button("Create preview", variant="primary", id="preview-confirm"),
                Button("Cancel", id="preview-cancel"),
                classes="preview-actions",
            )

    @on(Button.Pressed, "#preview-confirm")
    def confirm_pressed(self) -> None:
        text = self.query_one("#preview-path-input", Input).value.strip()
        if not text:
            return
        self.dismiss(Path(text).expanduser())

    @on(Button.Pressed, "#preview-cancel")
    def cancel_pressed(self) -> None:
        self.dismiss(None)

    @on(Input.Submitted, "#preview-path-input")
    def input_submitted(self) -> None:
        self.confirm_pressed()
