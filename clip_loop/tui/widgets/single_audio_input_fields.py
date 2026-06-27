"""Single-audio input tab fields."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Checkbox

from clip_loop.tui.widgets.field_label import FieldLabel
from clip_loop.tui.widgets.ms_preset_field import MsPresetField
from clip_loop.tui.widgets.path_browse_row import PathBrowseRow


class SingleAudioInputFields(Vertical):
    """Fields for one audio file in the Single tab."""

    DEFAULT_CSS = """
    SingleAudioInputFields {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield FieldLabel("External audio (optional)")
        yield PathBrowseRow(
            input_id="audio-path",
            browse_id="browse-audio",
            placeholder="path/to/audio.mp3",
        )
        yield MsPresetField(
            "Trim start",
            "audio-trim-preset",
            "audio-trim-custom",
            disabled=True,
        )
        yield Checkbox(
            "Ping-pong audio (--audio-alternate-reverse)",
            id="audio-alternate-reverse",
            disabled=True,
        )
