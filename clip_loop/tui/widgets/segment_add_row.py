"""Add-segment button row."""

from textual.containers import Horizontal


class SegmentAddRow(Horizontal):
    """Row containing an Add segment button."""

    DEFAULT_CSS = """
    SegmentAddRow {
        height: auto;
        align: right middle;
    }
    """
