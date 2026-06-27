"""Audio input section with single/multiple tabs."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import TabbedContent, TabPane

from clip_loop.tui.widgets.form_group_box import FormGroupBody, FormGroupBox, FormGroupTitle
from clip_loop.tui.widgets.multiple_audio_input_panel import MultipleAudioInputPanel
from clip_loop.tui.widgets.single_audio_input_fields import SingleAudioInputFields


class AudioInputSection(FormGroupBox):
    """Audio input form group with Single and Multiple tabs."""

    def compose(self) -> ComposeResult:
        yield FormGroupTitle("Audio input")
        with FormGroupBody():
            with TabbedContent(id="audio-input-tabs"):
                with TabPane("Single", id="audio-single-tab"):
                    yield SingleAudioInputFields()
                with TabPane("Multiple", id="audio-multiple-tab"):
                    yield MultipleAudioInputPanel()
