"""Field label widget."""

from textual.widgets import Label


class FieldLabel(Label):
    """Bold label above a form field."""

    DEFAULT_CSS = """
    FieldLabel {
        margin-top: 1;
        text-style: bold;
    }
    """
