"""Bordered form section container."""

from textual.containers import Container, Vertical
from textual.widgets import Label


class FormGroupBox(Container):
    """Bordered section grouping related fields."""

    DEFAULT_CSS = """
    FormGroupBox {
        border: round $primary;
        padding: 0 2;
        margin: 1 0;
        height: auto;
    }
    """


class FormGroupTitle(Label):
    """Title inside a form group box."""

    DEFAULT_CSS = """
    FormGroupTitle {
        text-style: bold;
        margin-bottom: 1;
        height: auto;
    }
    """


class FormGroupBody(Vertical):
    """Body content inside a form group box."""

    DEFAULT_CSS = """
    FormGroupBody {
        padding-left: 1;
        height: auto;
    }
    """
