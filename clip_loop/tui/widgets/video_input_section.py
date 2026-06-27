"""Video input section with single/multiple tabs."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import TabbedContent, TabPane

from clip_loop.tui.widgets.form_group_box import FormGroupBody, FormGroupBox, FormGroupTitle
from clip_loop.tui.widgets.multiple_video_input_panel import MultipleVideoInputPanel
from clip_loop.tui.widgets.single_video_input_fields import SingleVideoInputFields


class VideoInputSection(FormGroupBox):
    """Video input form group with Single and Multiple tabs."""

    def compose(self) -> ComposeResult:
        yield FormGroupTitle("Video input")
        with FormGroupBody():
            with TabbedContent(id="video-input-tabs"):
                with TabPane("Single", id="video-single-tab"):
                    yield SingleVideoInputFields()
                with TabPane("Multiple", id="video-multiple-tab"):
                    yield MultipleVideoInputPanel()
