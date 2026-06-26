"""Collapsible segment row base widget."""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Label


class CollapsibleSegmentRow(Vertical):
    """Reusable collapsible container used by segment rows."""

    ROW_PREFIX = ""
    TITLE_PREFIX = ""

    DEFAULT_CSS = """
    CollapsibleSegmentRow {
        border: solid $primary;
        padding: 0;
        margin: 1 0;
        height: auto;
    }
    .segment-header {
        height: 3;
        align: left middle;
        align-vertical: middle;
        padding: 0 1;
        margin-bottom: 0;
    }
    .segment-title {
        width: 1fr;
        text-style: bold;
        margin-top: 1;
    }
    .segment-toggle {
        width: 3;
        text-style: bold;
        margin-top: 1;
    }
    .segment-content {
        padding: 1 2;
        height: auto;
    }
    CollapsibleSegmentRow.-collapsed .segment-content {
        display: none;
    }
    """

    def __init__(self, index: int) -> None:
        super().__init__(id=f"{self.ROW_PREFIX}-{index}-row")
        self.index = index
        self.collapsed = False

    def _header(self) -> ComposeResult:
        prefix = f"{self.ROW_PREFIX}-{self.index}"
        with Horizontal(classes="segment-header"):
            yield Label("▼", classes="segment-toggle")
            yield Label(
                f"{self.TITLE_PREFIX} {self.index + 1}",
                classes="segment-title",
            )
            yield Button("Remove", id=f"{prefix}-remove", classes="segment-remove")

    def _content(self) -> ComposeResult:
        raise NotImplementedError

    def compose(self) -> ComposeResult:
        yield from self._header()
        with Vertical(classes="segment-content"):
            yield from self._content()

    def on_click(self, event: events.Click) -> None:
        widget = event.widget
        if not isinstance(widget, Widget):
            return
        if widget.has_class("segment-remove"):
            return
        if widget.has_class("segment-header") or widget.has_class("segment-title") or widget.has_class(
            "segment-toggle"
        ):
            self.toggle_collapse()

    def update_display_number(self, display_index: int) -> None:
        """Refresh the header label to match 1-based position in the list."""
        self.query_one(".segment-title", Label).update(
            f"{self.TITLE_PREFIX} {display_index + 1}"
        )

    def toggle_collapse(self) -> None:
        self.collapsed = not self.collapsed
        icon = self.query_one(".segment-toggle", Label)
        if self.collapsed:
            icon.update("▶")
            self.add_class("-collapsed")
        else:
            icon.update("▼")
            self.remove_class("-collapsed")
