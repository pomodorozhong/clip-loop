"""Compose the clip-loop TUI form layout."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import TabbedContent, TabPane

from clip_loop.tui.widgets import (
    AudioInputSection,
    AudioOptionsFields,
    DurationFields,
    OutputPathFields,
    ResolutionFields,
    VideoInputSection,
)


def compose_form() -> ComposeResult:
    """Yield the main configuration form widgets."""
    yield DurationFields()
    yield OutputPathFields()

    with TabbedContent(id="media-options-tabs"):
        with TabPane("Video", id="media-video-tab"):
            yield ResolutionFields()
            yield VideoInputSection()

        with TabPane("Audio", id="media-audio-tab"):
            yield AudioOptionsFields()
            yield AudioInputSection()
