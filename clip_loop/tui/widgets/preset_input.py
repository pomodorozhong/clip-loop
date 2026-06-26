"""Custom preset value input (hidden until preset is 'custom')."""

from textual.widgets import Input


class PresetInput(Input):
    """Input shown only when a paired Select is set to custom."""

    DEFAULT_CSS = """
    PresetInput {
        display: none;
    }
    """
