"""Run progress panel widget."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import LoadingIndicator, Static


class RunProgressPanel(Container):
    """Progress display shown while ffmpeg runs."""

    DEFAULT_CSS = """
    RunProgressPanel {
        display: none;
        height: auto;
        margin: 0 1;
        padding: 1;
        border: solid $primary;
        background: $surface;
    }
    RunProgressPanel.visible {
        display: block;
    }
    .run-progress-row {
        height: auto;
        align: left middle;
    }
    #run-spinner {
        width: auto;
        height: 3;
        min-height: 3;
        margin-right: 1;
    }
    .run-progress-text {
        height: auto;
        width: 1fr;
    }
    #run-message {
        text-style: bold;
    }
    #run-timer {
        color: $accent;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(classes="run-progress-row"):
            yield LoadingIndicator(id="run-spinner")
            with Vertical(classes="run-progress-text"):
                yield Static("Running ffmpeg…", id="run-message")
                yield Static("Elapsed: 0s", id="run-timer")
