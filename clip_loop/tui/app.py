"""Main Textual application for clip-loop."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Static

from clip_loop.last_run import load_last_run, save_last_run
from clip_loop.options import ClipLoopOptions
from clip_loop.pipeline import run_clip_loop
from clip_loop.tui.constants import HIGHLIGHTABLE_IDS, INVALID_CLASS
from clip_loop.tui.form import ClipLoopForm
from clip_loop.tui.handlers import FormHandlersMixin, register_handler_mixin
from clip_loop.tui.layout import compose_form
from clip_loop.tui.run_controller import RunController
from clip_loop.tui.run_progress import RunProgressController
from clip_loop.tui.validator import ClipLoopFormValidator
from clip_loop.tui.widgets import RunProgressPanel
from clip_loop.tui.segments import sync_row_custom_visibility, sync_video_row_crop

ClipLoopRunner = Callable[[ClipLoopOptions], Path]


class ClipLoopApp(FormHandlersMixin, App[None]):
    """Form-driven setup for clip-loop arguments."""

    TITLE = "clip-loop"

    DEFAULT_CSS = """
    Screen {
        layout: vertical;
    }
    VerticalScroll {
        height: 1fr;
        padding: 0 1;
    }
    Input.-invalid {
        border: tall $error;
    }
    Select.-invalid {
        border: tall $error;
    }
    TabbedContent {
        margin-bottom: 1;
        height: auto;
    }
    TabbedContent > ContentSwitcher {
        height: auto;
    }
    TabPane {
        height: auto;
        padding: 0 0 1 0;
    }
    #video-segments-list, #audio-segments-list {
        height: auto;
    }
    #status {
        height: auto;
        padding: 0 1;
        color: $warning;
    }
    #action-row {
        height: auto;
        padding: 0 1 1 1;
        align: center middle;
    }
    #action-row Button {
        margin-right: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+r", "run", "Run"),
    ]

    def __init__(
        self,
        *,
        initial_input: Path | None = None,
        initial_output: Path | None = None,
        initial_audio: Path | None = None,
        initial_options: ClipLoopOptions | None = None,
        runner: ClipLoopRunner | None = None,
    ) -> None:
        super().__init__()
        self._initial_input = initial_input
        self._initial_output = initial_output
        self._initial_audio = initial_audio
        self._initial_options = initial_options
        self._runner = runner or run_clip_loop
        self._form = ClipLoopForm(self)
        self._validator = ClipLoopFormValidator(self._form)
        self._progress = RunProgressController(self)
        self._run_controller = RunController(
            self,
            form=self._form,
            validator=self._validator,
            progress=self._progress,
            runner=self._runner,
            on_remember_last_run=self._remember_last_run,
            on_set_status=self._set_status,
            on_clear_highlights=self._clear_validation_highlights,
            on_set_highlights=self._set_validation_highlights,
            on_expand_sections=self._expand_sections_for,
        )
        self._last_run_options: ClipLoopOptions | None = None

    @property
    def _video_rows(self):
        return self._form.video_rows

    @property
    def _audio_rows(self):
        return self._form.audio_rows

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield from compose_form()
        yield RunProgressPanel(id="run-progress")
        yield Static("", id="status")
        with Horizontal(id="action-row"):
            yield Button("Run", variant="primary", id="run")
            yield Button("Apply last run", id="apply-last", disabled=True)
            yield Button("Quit", id="quit")
        yield Footer()

    async def on_mount(self) -> None:
        await self._video_rows.ensure_initial_rows()
        await self._audio_rows.ensure_initial_rows()
        if self._initial_options is not None:
            await self._form.apply(self._initial_options)
        else:
            if self._initial_input is not None:
                self.query_one("#input-path", Input).value = str(self._initial_input)
            if self._initial_output is not None:
                self.query_one("#output-path", Input).value = str(self._initial_output)
            if self._initial_audio is not None:
                self.query_one("#audio-path", Input).value = str(self._initial_audio)
        self._last_run_options = load_last_run()
        self._set_last_run_available(self._last_run_options is not None)
        self._sync_form_visibility()
        self._progress.on_mount()

    def _set_last_run_available(self, available: bool) -> None:
        self.query_one("#apply-last", Button).disabled = not available

    def _remember_last_run(self, options: ClipLoopOptions) -> None:
        self._last_run_options = options
        save_last_run(options)
        self._set_last_run_available(True)

    def _sync_form_visibility(self) -> None:
        self._form.sync_crop_options()
        self._form.sync_audio_options()
        self._form.sync_custom_visibility("duration-preset", "duration-custom")
        self._form.sync_custom_visibility("trim-preset", "trim-custom")
        self._form.sync_custom_visibility("speed-preset", "speed-custom")
        self._form.sync_custom_visibility("keep-ratio-preset", "keep-ratio-custom")
        self._form.sync_custom_visibility("audio-trim-preset", "audio-trim-custom")
        for preset_id, custom_id in (
            ("crossfade-preset", "crossfade-custom"),
            ("gap-preset", "gap-custom"),
            ("seam-fade-preset", "seam-fade-custom"),
        ):
            self._form.sync_custom_visibility(preset_id, custom_id)
        for row in self._video_rows._rows():
            prefix = f"video-seg-{row.index}"
            sync_row_custom_visibility(row, f"#{prefix}-trim-preset", f"#{prefix}-trim-custom")
            sync_row_custom_visibility(row, f"#{prefix}-speed-preset", f"#{prefix}-speed-custom")
            sync_row_custom_visibility(
                row, f"#{prefix}-keep-ratio-preset", f"#{prefix}-keep-ratio-custom"
            )
            sync_video_row_crop(row)
        for row in self._audio_rows._rows():
            prefix = f"audio-seg-{row.index}"
            sync_row_custom_visibility(row, f"#{prefix}-trim-preset", f"#{prefix}-trim-custom")

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def _clear_validation_highlights(self) -> None:
        for widget_id in HIGHLIGHTABLE_IDS:
            widget = self.query(widget_id).first()
            if widget is not None:
                widget.remove_class(INVALID_CLASS)
        for row in self._video_rows._rows():
            for child in row.walk_children(with_self=True):
                child.remove_class(INVALID_CLASS)
        for row in self._audio_rows._rows():
            for child in row.walk_children(with_self=True):
                child.remove_class(INVALID_CLASS)

    def _set_validation_highlights(self, widget_ids: list[str]) -> None:
        self._clear_validation_highlights()
        for widget_id in widget_ids:
            self.query_one(widget_id).add_class(INVALID_CLASS)


register_handler_mixin(ClipLoopApp, FormHandlersMixin)
