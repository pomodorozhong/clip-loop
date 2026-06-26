"""Horizontal row for path input and browse button."""

from textual.containers import Horizontal


class FieldRow(Horizontal):
    """Path input plus optional browse button."""

    DEFAULT_CSS = """
    FieldRow {
        height: auto;
        margin-bottom: 1;
    }
    FieldRow Input {
        width: 1fr;
    }
    """
