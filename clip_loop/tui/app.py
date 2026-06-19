"""Main Textual application for clip-loop."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Checkbox,
    Collapsible,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
    Select,
    Static,
)

from clip_loop.errors import ClipLoopError
from clip_loop.file_dialog import (
    AUDIO_EXTENSIONS,
    VIDEO_EXTENSIONS,
    native_file_dialog_available,
    pick_open_file,
    pick_save_file,
)
from clip_loop.options import ClipLoopOptions
from clip_loop.pipeline import run_clip_loop

from clip_loop.tui.constants import (
    APP_CSS,
    AUDIO_SECTION_IDS,
    CROP_CORNER_PRESETS,
    DURATION_PRESETS,
    HIGHLIGHTABLE_IDS,
    INVALID_CLASS,
    KEEP_RATIO_PRESETS,
    MS_PRESETS,
    SPEED_PRESETS,
    VIDEO_SECTION_IDS,
)
from clip_loop.tui.form import ClipLoopForm
from clip_loop.tui.run_progress import RunProgressController
from clip_loop.tui.screens import FilePickScreen
from clip_loop.tui.validator import ClipLoopFormValidator

ClipLoopRunner = Callable[[ClipLoopOptions], Path]


class ClipLoopApp(App[None]):
    """Form-driven setup for clip-loop arguments."""

    TITLE = "clip-loop"
    CSS = APP_CSS

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
        runner: ClipLoopRunner | None = None,
    ) -> None:
        super().__init__()
        self._initial_input = initial_input
        self._initial_output = initial_output
        self._initial_audio = initial_audio
        self._runner = runner or run_clip_loop
        self._form = ClipLoopForm(self)
        self._validator = ClipLoopFormValidator(self._form)
        self._progress = RunProgressController(self)

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Label("Input video", classes="field-label")
            with Horizontal(classes="field-row"):
                yield Input(
                    placeholder="path/to/clip.mp4",
                    id="input-path",
                )
                yield Button("Browse…", id="browse-input")

            yield Label("Target duration", classes="field-label")
            yield Select(DURATION_PRESETS, id="duration-preset", value="1h")
            yield Input(
                placeholder="e.g. 45m or 3600",
                id="duration-custom",
                classes="hidden-custom",
            )

            yield Label("Output file (optional)", classes="field-label")
            with Horizontal(classes="field-row"):
                yield Input(
                    placeholder="default: <stem>_looped<suffix>",
                    id="output-path",
                )
                yield Button("Browse…", id="browse-output")

            with Collapsible(title="Video options", collapsed=False, id="video-collapsible"):
                yield Checkbox(
                    "Ping-pong video (--alternate-reverse)",
                    id="alternate-reverse",
                )
                yield Label("Trim start", classes="field-label")
                yield Select(MS_PRESETS, id="trim-preset", value="0")
                yield Input(
                    placeholder="milliseconds",
                    id="trim-custom",
                    classes="hidden-custom",
                )
                yield Label("Playback speed", classes="field-label")
                yield Select(SPEED_PRESETS, id="speed-preset", value="100")
                yield Input(
                    placeholder="e.g. 80 or 120",
                    id="speed-custom",
                    classes="hidden-custom",
                )
                yield Label("Crop before loop", classes="field-label")
                yield Select(KEEP_RATIO_PRESETS, id="keep-ratio-preset", value="off")
                yield Input(
                    placeholder="e.g. 75% or 0.75",
                    id="keep-ratio-custom",
                    classes="hidden-custom",
                    disabled=True,
                )
                yield Label("Crop corner", classes="field-label")
                yield Select(
                    CROP_CORNER_PRESETS,
                    id="crop-corner",
                    value="top_left",
                    disabled=True,
                )

            with Collapsible(title="Audio options", collapsed=True, id="audio-collapsible"):
                yield Label("External audio (optional)", classes="field-label")
                with Horizontal(classes="field-row"):
                    yield Input(
                        placeholder="path/to/audio.mp3",
                        id="audio-path",
                    )
                    yield Button("Browse…", id="browse-audio")
                yield Checkbox(
                    "Ping-pong audio (--audio-alternate-reverse)",
                    id="audio-alternate-reverse",
                    disabled=True,
                )
                yield Label("Crossfade at seams", classes="field-label")
                yield Select(
                    MS_PRESETS,
                    id="crossfade-preset",
                    value="0",
                    disabled=True,
                )
                yield Input(
                    placeholder="milliseconds",
                    id="crossfade-custom",
                    classes="hidden-custom",
                    disabled=True,
                )
                yield Label("Silence gap between clips", classes="field-label")
                yield Select(MS_PRESETS, id="gap-preset", value="0", disabled=True)
                yield Input(
                    placeholder="milliseconds",
                    id="gap-custom",
                    classes="hidden-custom",
                    disabled=True,
                )
                yield Label("Seam fade in/out", classes="field-label")
                yield Select(
                    MS_PRESETS,
                    id="seam-fade-preset",
                    value="0",
                    disabled=True,
                )
                yield Input(
                    placeholder="milliseconds",
                    id="seam-fade-custom",
                    classes="hidden-custom",
                    disabled=True,
                )

        with Container(id="run-progress"):
            with Horizontal(classes="run-progress-row"):
                yield LoadingIndicator(id="run-spinner")
                with Vertical(classes="run-progress-text"):
                    yield Static("Running ffmpeg…", id="run-message")
                    yield Static("Elapsed: 0s", id="run-timer")
        yield Static("", id="status")
        with Horizontal(id="action-row"):
            yield Button("Run", variant="primary", id="run")
            yield Button("Quit", id="quit")
        yield Footer()

    def on_mount(self) -> None:
        if self._initial_input is not None:
            self.query_one("#input-path", Input).value = str(self._initial_input)
        if self._initial_output is not None:
            self.query_one("#output-path", Input).value = str(self._initial_output)
        if self._initial_audio is not None:
            self.query_one("#audio-path", Input).value = str(self._initial_audio)
        self._form.sync_crop_options()
        self._form.sync_audio_options()
        self._form.sync_custom_visibility("duration-preset", "duration-custom")
        self._form.sync_custom_visibility("trim-preset", "trim-custom")
        self._form.sync_custom_visibility("speed-preset", "speed-custom")
        self._form.sync_custom_visibility("keep-ratio-preset", "keep-ratio-custom")
        for preset_id, custom_id in (
            ("crossfade-preset", "crossfade-custom"),
            ("gap-preset", "gap-custom"),
            ("seam-fade-preset", "seam-fade-custom"),
        ):
            self._form.sync_custom_visibility(preset_id, custom_id)
        self._progress.on_mount()

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def _clear_validation_highlights(self) -> None:
        for widget_id in HIGHLIGHTABLE_IDS:
            widget = self.query(widget_id).first()
            if widget is not None:
                widget.remove_class(INVALID_CLASS)

    def _set_validation_highlights(self, widget_ids: list[str]) -> None:
        self._clear_validation_highlights()
        for widget_id in widget_ids:
            self.query_one(widget_id).add_class(INVALID_CLASS)

    def _expand_sections_for(self, widget_ids: list[str]) -> None:
        if AUDIO_SECTION_IDS.intersection(widget_ids):
            self.query_one("#audio-collapsible", Collapsible).collapsed = False
        if VIDEO_SECTION_IDS.intersection(widget_ids):
            self.query_one("#video-collapsible", Collapsible).collapsed = False

    @work(exclusive=True)
    async def _browse_into_input(
        self,
        input_id: str,
        start: Path,
        *,
        save: bool = False,
    ) -> None:
        if save:
            start_dir, default_name = self._form.browse_save_defaults(input_id)
            picked = await asyncio.to_thread(
                pick_save_file,
                title="Save output as",
                start=start_dir,
                default_name=default_name,
            )
        elif input_id == "#audio-path":
            picked = await asyncio.to_thread(
                pick_open_file,
                title="Select audio file",
                start=start,
                extensions=AUDIO_EXTENSIONS,
            )
        else:
            picked = await asyncio.to_thread(
                pick_open_file,
                title="Select video file",
                start=start,
                extensions=VIDEO_EXTENSIONS,
            )
        if picked is None:
            if native_file_dialog_available():
                return
            picked = await self.push_screen_wait(FilePickScreen(start=start))
        if picked is not None:
            self.query_one(input_id, Input).value = str(picked)
            if input_id == "#audio-path":
                self._form.sync_audio_options()

    @on(Input.Changed, "#audio-path")
    def audio_path_changed(self, event: Input.Changed) -> None:
        event.input.remove_class(INVALID_CLASS)
        self._form.sync_audio_options()

    @on(Input.Changed)
    def input_clear_invalid(self, event: Input.Changed) -> None:
        event.input.remove_class(INVALID_CLASS)

    @on(Select.Changed)
    def select_clear_invalid(self, event: Select.Changed) -> None:
        event.select.remove_class(INVALID_CLASS)

    @on(Select.Changed, "#duration-preset")
    def duration_preset_changed(self) -> None:
        self._form.sync_custom_visibility("duration-preset", "duration-custom")

    @on(Select.Changed, "#keep-ratio-preset")
    def keep_ratio_preset_changed(self) -> None:
        self._form.sync_crop_options()
        self._form.sync_custom_visibility("keep-ratio-preset", "keep-ratio-custom")

    @on(Select.Changed, "#trim-preset")
    def trim_preset_changed(self) -> None:
        self._form.sync_custom_visibility("trim-preset", "trim-custom")

    @on(Select.Changed, "#speed-preset")
    def speed_preset_changed(self) -> None:
        self._form.sync_custom_visibility("speed-preset", "speed-custom")

    @on(Select.Changed, "#crossfade-preset")
    def crossfade_preset_changed(self) -> None:
        self._form.sync_custom_visibility("crossfade-preset", "crossfade-custom")

    @on(Select.Changed, "#gap-preset")
    def gap_preset_changed(self) -> None:
        self._form.sync_custom_visibility("gap-preset", "gap-custom")

    @on(Select.Changed, "#seam-fade-preset")
    def seam_fade_preset_changed(self) -> None:
        self._form.sync_custom_visibility("seam-fade-preset", "seam-fade-custom")

    @on(Button.Pressed, "#browse-input")
    def browse_input(self) -> None:
        self._browse_into_input("#input-path", self._form.browse_start_dir("#input-path"))

    @on(Button.Pressed, "#browse-output")
    def browse_output(self) -> None:
        self._browse_into_input(
            "#output-path",
            self._form.browse_start_dir("#output-path"),
            save=True,
        )

    @on(Button.Pressed, "#browse-audio")
    def browse_audio(self) -> None:
        self._browse_into_input("#audio-path", self._form.browse_start_dir("#audio-path"))

    @on(Button.Pressed, "#quit")
    def quit_pressed(self) -> None:
        self.exit()

    def action_run(self) -> None:
        self.query_one("#run", Button).press()

    @on(Button.Pressed, "#run")
    def run_pressed(self) -> None:
        self._start_run()

    def _start_run(self) -> None:
        result = self._validator.validate()
        if not result.ok:
            self._set_validation_highlights(result.highlight_widget_ids)
            self._expand_sections_for(result.highlight_widget_ids)
            if result.highlight_widget_ids:
                self.query_one(result.highlight_widget_ids[0]).focus()
            self._set_status(result.error_message or "")
            return

        self._clear_validation_highlights()
        self.query_one("#run", Button).disabled = True
        self.query_one("#quit", Button).disabled = True
        self._set_status("")
        self._progress.show()
        options = self._form.collect()
        self._run_job_worker(options)

    @work(thread=True, exclusive=True)
    def _run_job_worker(self, options: ClipLoopOptions) -> None:
        try:
            output = self._runner(options)
        except SystemExit:
            self.call_from_thread(
                self._on_run_failed,
                "Processing failed (ffmpeg error). See terminal output if any.",
            )
            return
        except (ClipLoopError, ValueError, OSError) as exc:
            self.call_from_thread(self._on_run_failed, str(exc))
            return
        self.call_from_thread(self._on_run_done, output, options.duration)

    def _finish_run(self, message: str) -> None:
        from clip_loop.parsing import format_elapsed

        elapsed = self._progress.capture_elapsed()
        self._progress.hide()
        if elapsed is not None:
            message = f"{message} in {format_elapsed(elapsed)}"
        self._set_status(message)
        self.query_one("#run", Button).disabled = False
        self.query_one("#quit", Button).disabled = False

    def _on_run_failed(self, message: str) -> None:
        self._finish_run(message)

    def _on_run_done(self, output: Path, duration: float) -> None:
        self._finish_run(f"Wrote {output} ({duration:g}s target)")
