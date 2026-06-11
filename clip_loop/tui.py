"""Interactive terminal UI for configuring and running clip-loop."""

from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.timer import Timer
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Collapsible,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
    Select,
    Static,
)

from clip_loop.cli import (
    ClipLoopError,
    format_elapsed,
    parse_crop_corner,
    parse_duration,
    parse_keep_ratio,
    parse_speed_percent,
    run_clip_loop,
    validate_clip_loop_options,
)
from clip_loop.file_dialog import (
    AUDIO_EXTENSIONS,
    VIDEO_EXTENSIONS,
    native_file_dialog_available,
    pick_open_file,
    pick_save_file,
)

INVALID_CLASS = "-invalid"

HIGHLIGHTABLE_IDS = (
    "#input-path",
    "#duration-preset",
    "#duration-custom",
    "#output-path",
    "#audio-path",
    "#trim-preset",
    "#trim-custom",
    "#speed-preset",
    "#speed-custom",
    "#keep-ratio-preset",
    "#keep-ratio-custom",
    "#crop-corner",
    "#crossfade-preset",
    "#crossfade-custom",
    "#gap-preset",
    "#gap-custom",
    "#seam-fade-preset",
    "#seam-fade-custom",
)

AUDIO_SECTION_IDS = frozenset(
    {
        "#audio-path",
        "#audio-alternate-reverse",
        "#crossfade-preset",
        "#crossfade-custom",
        "#gap-preset",
        "#gap-custom",
        "#seam-fade-preset",
        "#seam-fade-custom",
    }
)
VIDEO_SECTION_IDS = frozenset(
    {
        "#trim-preset",
        "#trim-custom",
        "#speed-preset",
        "#speed-custom",
        "#keep-ratio-preset",
        "#keep-ratio-custom",
        "#crop-corner",
    }
)
KEEP_RATIO_PRESETS: tuple[tuple[str, str], ...] = (
    ("Off", "off"),
    ("90%", "90%"),
    ("80%", "80%"),
    ("50%", "50%"),
    ("Custom…", "custom"),
)

CROP_CORNER_PRESETS: tuple[tuple[str, str], ...] = (
    ("Top left (keep bottom-right)", "top_left"),
    ("Top right (keep bottom-left)", "top_right"),
    ("Bottom left (keep top-right)", "bottom_left"),
    ("Bottom right (keep top-left)", "bottom_right"),
)

DURATION_PRESETS: tuple[tuple[str, str], ...] = (
    ("90 seconds", "90s"),
    ("10 minutes", "10m"),
    ("1 hour", "1h"),
    ("6 hours", "6h"),
    ("8 hours", "8h"),
    ("Custom…", "custom"),
)

MS_PRESETS: tuple[tuple[str, str], ...] = (
    ("Off (0)", "0"),
    ("50 ms", "50"),
    ("120 ms", "120"),
    ("250 ms", "250"),
    ("500 ms", "500"),
    ("1000 ms", "1000"),
    ("Custom…", "custom"),
)

SPEED_PRESETS: tuple[tuple[str, str], ...] = (
    ("50%", "50"),
    ("80%", "80"),
    ("100% (normal)", "100"),
    ("120%", "120"),
    ("150%", "150"),
    ("Custom…", "custom"),
)


class FilePickScreen(ModalScreen[Path | None]):
    """Pick a file from the filesystem."""

    BINDINGS = [("escape", "dismiss", "Cancel")]

    def __init__(self, start: Path | None = None) -> None:
        super().__init__()
        self._start = start or Path.cwd()

    def compose(self) -> ComposeResult:
        yield DirectoryTree(str(self._start))
        yield Horizontal(
            Button("Select", variant="primary", id="pick-select"),
            Button("Cancel", id="pick-cancel"),
            classes="pick-actions",
        )

    def _selected_path(self) -> Path | None:
        tree = self.query_one(DirectoryTree)
        node = tree.cursor_node
        if node is None or node.data is None:
            return None
        path = node.data.path
        return path if path.is_file() else None

    @on(Button.Pressed, "#pick-select")
    def select_pressed(self) -> None:
        path = self._selected_path()
        if path is not None:
            self.dismiss(path)

    @on(Button.Pressed, "#pick-cancel")
    def cancel_pressed(self) -> None:
        self.dismiss(None)

    @on(DirectoryTree.FileSelected)
    def file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.dismiss(Path(event.path))


def _ms_from_select(select: Select[str], custom: Input) -> int:
    value = select.value
    if value is Select.BLANK:
        return 0
    if value == "custom":
        text = custom.value.strip()
        if not text:
            return 0
        return int(text)
    return int(value)


def _duration_from_form(select: Select[str], custom: Input) -> float:
    value = select.value
    if value is Select.BLANK or value == "custom":
        text = custom.value.strip() or "1h"
        return parse_duration(text)
    return parse_duration(value)


def _is_crop_enabled(select: Select[str]) -> bool:
    value = select.value
    return value is not Select.BLANK and value != "off"


def _keep_ratio_from_form(select: Select[str], custom: Input) -> float:
    value = select.value
    if value is Select.BLANK or value == "off":
        raise ValueError("crop is disabled")
    if value == "custom":
        text = custom.value.strip() or "80%"
        return parse_keep_ratio(text)
    return parse_keep_ratio(value)


def _speed_from_form(select: Select[str], custom: Input) -> float:
    value = select.value
    if value is Select.BLANK or value == "100":
        return 100.0
    if value == "custom":
        text = custom.value.strip() or "100"
        return parse_speed_percent(text)
    return parse_speed_percent(value)


def _widget_for_clip_loop_error(message: str, *, duration_is_custom: bool) -> str:
    if "Input not found" in message:
        return "#input-path"
    if "Audio input not found" in message:
        return "#audio-path"
    if "requires --audio" in message:
        return "#audio-path"
    if "Duration must be positive" in message or "duration cannot be empty" in message:
        return "#duration-custom" if duration_is_custom else "#duration-preset"
    if "keep ratio" in message.lower():
        return "#keep-ratio-custom" if "custom" in message else "#keep-ratio-preset"
    if "speed" in message.lower():
        return "#speed-custom" if "custom" in message else "#speed-preset"
    if "--corner" in message or "corner must be" in message.lower():
        return "#crop-corner"
    if "Invalid crop" in message:
        return "#keep-ratio-preset"
    return "#input-path"


class ClipLoopApp(App[None]):
    """Form-driven setup for clip-loop arguments."""

    TITLE = "clip-loop"
    CSS = """
    Screen {
        layout: vertical;
    }
    VerticalScroll {
        height: 1fr;
        padding: 0 1;
    }
    .field-label {
        margin-top: 1;
        text-style: bold;
    }
    .field-row {
        height: auto;
        margin-bottom: 1;
    }
    .field-row Input {
        width: 1fr;
    }
    Input.-invalid {
        border: tall $error;
    }
    Select.-invalid {
        border: tall $error;
    }
    Collapsible {
        margin: 1 0;
        border: solid $primary;
        padding: 0 1 1 1;
    }
    #run-progress {
        display: none;
        height: auto;
        margin: 0 1;
        padding: 1;
        border: solid $primary;
        background: $surface;
    }
    #run-progress.visible {
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
    FilePickScreen DirectoryTree {
        height: 1fr;
    }
    .pick-actions {
        height: auto;
        padding: 1;
        align: center middle;
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
    ) -> None:
        super().__init__()
        self._initial_input = initial_input
        self._initial_output = initial_output
        self._initial_audio = initial_audio
        self._run_started: float | None = None
        self._run_timer: Timer | None = None

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
        self._sync_crop_options()
        self._sync_audio_options()
        self._sync_custom_visibility("duration-preset", "duration-custom")
        self._sync_custom_visibility("trim-preset", "trim-custom")
        self._sync_custom_visibility("speed-preset", "speed-custom")
        self._sync_custom_visibility("keep-ratio-preset", "keep-ratio-custom")
        for preset_id, custom_id in (
            ("crossfade-preset", "crossfade-custom"),
            ("gap-preset", "gap-custom"),
            ("seam-fade-preset", "seam-fade-custom"),
        ):
            self._sync_custom_visibility(preset_id, custom_id)
        self._run_timer = self.set_interval(
            0.25, self._update_run_timer, name="run_elapsed", pause=True
        )

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

    def _sync_crop_options(self) -> None:
        enabled = _is_crop_enabled(self.query_one("#keep-ratio-preset", Select))
        custom = self.query_one("#keep-ratio-custom")
        corner = self.query_one("#crop-corner")
        custom.disabled = not enabled
        corner.disabled = not enabled
        if enabled:
            self._sync_custom_visibility("keep-ratio-preset", "keep-ratio-custom")
        else:
            custom.display = False

    def _validate_before_run(self) -> str | None:
        highlights: list[str] = []
        errors: list[str] = []

        input_text = self.query_one("#input-path", Input).value.strip()
        input_path: Path | None = None
        if not input_text:
            highlights.append("#input-path")
            errors.append("Input video path is required.")
        else:
            input_path = Path(input_text)
            if not input_path.is_file():
                highlights.append("#input-path")
                errors.append(f"Input not found: {input_path}")

        duration_select = self.query_one("#duration-preset", Select)
        duration_custom = self.query_one("#duration-custom", Input)
        duration_is_custom = duration_select.value == "custom"
        duration_ok = True
        duration = 0.0
        try:
            duration = _duration_from_form(duration_select, duration_custom)
        except (ValueError, argparse.ArgumentTypeError):
            duration_ok = False
            highlights.append(
                "#duration-custom" if duration_is_custom else "#duration-preset"
            )
            errors.append("Invalid duration.")
        if duration_ok and duration <= 0:
            highlights.append(
                "#duration-custom" if duration_is_custom else "#duration-preset"
            )
            errors.append("Duration must be positive.")

        audio_text = self.query_one("#audio-path", Input).value.strip()
        audio_path = Path(audio_text) if audio_text else None

        trim_select = self.query_one("#trim-preset", Select)
        trim_custom = self.query_one("#trim-custom", Input)
        trim_start_ms = 0
        try:
            trim_start_ms = _ms_from_select(trim_select, trim_custom)
        except ValueError:
            highlights.append(
                "#trim-custom" if trim_select.value == "custom" else "#trim-preset"
            )
            errors.append("Invalid trim start value.")

        speed_select = self.query_one("#speed-preset", Select)
        speed_custom = self.query_one("#speed-custom", Input)
        speed_is_custom = speed_select.value == "custom"
        speed_percent = 100.0
        try:
            speed_percent = _speed_from_form(speed_select, speed_custom)
        except (ValueError, argparse.ArgumentTypeError):
            highlights.append(
                "#speed-custom" if speed_is_custom else "#speed-preset"
            )
            errors.append("Invalid playback speed.")

        keep_ratio_select = self.query_one("#keep-ratio-preset", Select)
        keep_ratio_custom = self.query_one("#keep-ratio-custom", Input)
        crop_enabled = _is_crop_enabled(keep_ratio_select)
        keep_ratio: float | None = None
        crop_corner: str | None = None
        if crop_enabled:
            keep_ratio_is_custom = keep_ratio_select.value == "custom"
            try:
                keep_ratio = _keep_ratio_from_form(keep_ratio_select, keep_ratio_custom)
            except (ValueError, argparse.ArgumentTypeError):
                highlights.append(
                    "#keep-ratio-custom"
                    if keep_ratio_is_custom
                    else "#keep-ratio-preset"
                )
                errors.append("Invalid keep ratio.")
            corner_select = self.query_one("#crop-corner", Select)
            if corner_select.value is Select.BLANK:
                highlights.append("#crop-corner")
                errors.append("Crop corner is required.")
            else:
                try:
                    crop_corner = parse_crop_corner(corner_select.value)
                except argparse.ArgumentTypeError:
                    highlights.append("#crop-corner")
                    errors.append("Invalid crop corner.")

        crossfade_select = self.query_one("#crossfade-preset", Select)
        crossfade_custom = self.query_one("#crossfade-custom", Input)
        gap_select = self.query_one("#gap-preset", Select)
        gap_custom = self.query_one("#gap-custom", Input)
        seam_select = self.query_one("#seam-fade-preset", Select)
        seam_custom = self.query_one("#seam-fade-custom", Input)

        ms_fields: list[tuple[Select[str], Input, str, str]] = [
            (crossfade_select, crossfade_custom, "crossfade", "#crossfade-preset"),
            (gap_select, gap_custom, "gap", "#gap-preset"),
            (seam_select, seam_custom, "seam fade", "#seam-fade-preset"),
        ]
        audio_crossfade_ms = 0
        audio_gap_ms = 0
        audio_seam_fade_ms = 0
        for select, custom, label, preset_id in ms_fields:
            try:
                ms = _ms_from_select(select, custom)
            except ValueError:
                widget_id = (
                    preset_id.replace("-preset", "-custom")
                    if select.value == "custom"
                    else preset_id
                )
                highlights.append(widget_id)
                errors.append(f"Invalid {label} value.")
                continue
            if preset_id == "#crossfade-preset":
                audio_crossfade_ms = ms
            elif preset_id == "#gap-preset":
                audio_gap_ms = ms
            else:
                audio_seam_fade_ms = ms

        if input_path is not None and duration_ok and not errors:
            try:
                validate_clip_loop_options(
                    input_path=input_path,
                    duration=duration,
                    trim_start_ms=trim_start_ms,
                    audio_path=audio_path,
                    audio_alternate_reverse=self.query_one(
                        "#audio-alternate-reverse", Checkbox
                    ).value,
                    audio_crossfade_ms=audio_crossfade_ms,
                    audio_gap_ms=audio_gap_ms,
                    audio_seam_fade_ms=audio_seam_fade_ms,
                    keep_ratio=keep_ratio,
                    crop_corner=crop_corner,
                    speed_percent=speed_percent,
                )
            except ClipLoopError as exc:
                widget_id = _widget_for_clip_loop_error(
                    str(exc), duration_is_custom=duration_is_custom
                )
                highlights.append(widget_id)
                errors.append(str(exc))

        if not errors:
            return None

        unique_highlights = list(dict.fromkeys(highlights))
        self._set_validation_highlights(unique_highlights)
        self._expand_sections_for(unique_highlights)
        self.query_one(unique_highlights[0]).focus()
        return "; ".join(errors)

    def _show_run_progress(self) -> None:
        self._run_started = time.perf_counter()
        self.query_one("#run-progress").add_class("visible")
        self.query_one("#run-timer", Static).update("Elapsed: 0s")
        self._update_run_timer()
        if self._run_timer is not None:
            self._run_timer.resume()

    def _hide_run_progress(self) -> None:
        self.query_one("#run-progress").remove_class("visible")
        self._run_started = None
        if self._run_timer is not None:
            self._run_timer.pause()

    def _capture_elapsed(self) -> float | None:
        if self._run_started is None:
            return None
        return time.perf_counter() - self._run_started

    def _update_run_timer(self) -> None:
        if self._run_started is None:
            return
        elapsed = time.perf_counter() - self._run_started
        self.query_one("#run-timer", Static).update(
            f"Elapsed: {format_elapsed(elapsed)}"
        )

    def _has_audio_path(self) -> bool:
        return bool(self.query_one("#audio-path", Input).value.strip())

    def _sync_audio_options(self) -> None:
        has_audio = self._has_audio_path()
        for selector in (
            "#audio-alternate-reverse",
            "#crossfade-preset",
            "#crossfade-custom",
            "#gap-preset",
            "#gap-custom",
            "#seam-fade-preset",
            "#seam-fade-custom",
        ):
            self.query_one(selector).disabled = not has_audio
        if has_audio:
            self.query_one("#audio-collapsible", Collapsible).collapsed = False

    def _sync_custom_visibility(self, preset_id: str, custom_id: str) -> None:
        select = self.query_one(f"#{preset_id}", Select)
        custom = self.query_one(f"#{custom_id}", Input)
        show = select.value == "custom"
        custom.display = show
        if not show:
            custom.value = ""

    def _browse_start_dir(self, input_id: str) -> Path:
        text = self.query_one(input_id, Input).value.strip() or "."
        start = Path(text)
        return start.parent if start.suffix else start

    def _browse_save_defaults(self, input_id: str) -> tuple[Path, str]:
        text = self.query_one(input_id, Input).value.strip()
        if text:
            path = Path(text)
            if path.suffix:
                return path.parent, path.name
            return path, "output.mp4"
        input_text = self.query_one("#input-path", Input).value.strip()
        if input_text:
            source = Path(input_text)
            return source.parent, f"{source.stem}_looped{source.suffix or '.mp4'}"
        return Path.home(), "output.mp4"

    @work(exclusive=True)
    async def _browse_into_input(
        self,
        input_id: str,
        start: Path,
        *,
        save: bool = False,
    ) -> None:
        if save:
            start_dir, default_name = self._browse_save_defaults(input_id)
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
                self._sync_audio_options()

    @on(Input.Changed, "#audio-path")
    def audio_path_changed(self, event: Input.Changed) -> None:
        event.input.remove_class(INVALID_CLASS)
        self._sync_audio_options()

    @on(Input.Changed)
    def input_clear_invalid(self, event: Input.Changed) -> None:
        event.input.remove_class(INVALID_CLASS)

    @on(Select.Changed)
    def select_clear_invalid(self, event: Select.Changed) -> None:
        event.select.remove_class(INVALID_CLASS)

    @on(Select.Changed, "#duration-preset")
    def duration_preset_changed(self) -> None:
        self._sync_custom_visibility("duration-preset", "duration-custom")

    @on(Select.Changed, "#keep-ratio-preset")
    def keep_ratio_preset_changed(self) -> None:
        self._sync_crop_options()
        self._sync_custom_visibility("keep-ratio-preset", "keep-ratio-custom")

    @on(Select.Changed, "#trim-preset")
    def trim_preset_changed(self) -> None:
        self._sync_custom_visibility("trim-preset", "trim-custom")

    @on(Select.Changed, "#speed-preset")
    def speed_preset_changed(self) -> None:
        self._sync_custom_visibility("speed-preset", "speed-custom")

    @on(Select.Changed, "#crossfade-preset")
    def crossfade_preset_changed(self) -> None:
        self._sync_custom_visibility("crossfade-preset", "crossfade-custom")

    @on(Select.Changed, "#gap-preset")
    def gap_preset_changed(self) -> None:
        self._sync_custom_visibility("gap-preset", "gap-custom")

    @on(Select.Changed, "#seam-fade-preset")
    def seam_fade_preset_changed(self) -> None:
        self._sync_custom_visibility("seam-fade-preset", "seam-fade-custom")

    @on(Button.Pressed, "#browse-input")
    def browse_input(self) -> None:
        self._browse_into_input("#input-path", self._browse_start_dir("#input-path"))

    @on(Button.Pressed, "#browse-output")
    def browse_output(self) -> None:
        self._browse_into_input(
            "#output-path",
            self._browse_start_dir("#output-path"),
            save=True,
        )

    @on(Button.Pressed, "#browse-audio")
    def browse_audio(self) -> None:
        self._browse_into_input("#audio-path", self._browse_start_dir("#audio-path"))

    @on(Button.Pressed, "#quit")
    def quit_pressed(self) -> None:
        self.exit()

    def action_run(self) -> None:
        self.query_one("#run", Button).press()

    @on(Button.Pressed, "#run")
    def run_pressed(self) -> None:
        self._start_run()

    def _collect_options(self) -> dict:
        input_text = self.query_one("#input-path", Input).value.strip()
        output_text = self.query_one("#output-path", Input).value.strip()
        output_path = Path(output_text) if output_text else None
        keep_ratio_select = self.query_one("#keep-ratio-preset", Select)
        keep_ratio: float | None = None
        crop_corner: str | None = None
        if _is_crop_enabled(keep_ratio_select):
            keep_ratio = _keep_ratio_from_form(
                keep_ratio_select,
                self.query_one("#keep-ratio-custom", Input),
            )
            crop_corner = parse_crop_corner(
                self.query_one("#crop-corner", Select).value
            )
        audio_text = self.query_one("#audio-path", Input).value.strip()
        return {
            "input_path": Path(input_text),
            "duration": _duration_from_form(
                self.query_one("#duration-preset", Select),
                self.query_one("#duration-custom", Input),
            ),
            "output_path": output_path,
            "alternate_reverse": self.query_one("#alternate-reverse", Checkbox).value,
            "trim_start_ms": _ms_from_select(
                self.query_one("#trim-preset", Select),
                self.query_one("#trim-custom", Input),
            ),
            "audio_path": Path(audio_text) if audio_text else None,
            "audio_alternate_reverse": self.query_one(
                "#audio-alternate-reverse", Checkbox
            ).value,
            "audio_crossfade_ms": _ms_from_select(
                self.query_one("#crossfade-preset", Select),
                self.query_one("#crossfade-custom", Input),
            ),
            "audio_gap_ms": _ms_from_select(
                self.query_one("#gap-preset", Select),
                self.query_one("#gap-custom", Input),
            ),
            "audio_seam_fade_ms": _ms_from_select(
                self.query_one("#seam-fade-preset", Select),
                self.query_one("#seam-fade-custom", Input),
            ),
            "keep_ratio": keep_ratio,
            "crop_corner": crop_corner,
            "speed_percent": _speed_from_form(
                self.query_one("#speed-preset", Select),
                self.query_one("#speed-custom", Input),
            ),
        }

    def _start_run(self) -> None:
        error = self._validate_before_run()
        if error is not None:
            self._set_status(error)
            return
        self._clear_validation_highlights()
        self.query_one("#run", Button).disabled = True
        self.query_one("#quit", Button).disabled = True
        self._set_status("")
        self._show_run_progress()
        # Widget state must be read on the main thread before the worker runs.
        self._run_job_worker(self._collect_options())

    @work(thread=True, exclusive=True)
    def _run_job_worker(self, opts: dict) -> None:
        try:
            output = run_clip_loop(**opts)
        except SystemExit:
            self.call_from_thread(
                self._on_run_failed,
                "Processing failed (ffmpeg error). See terminal output if any.",
            )
            return
        except (ClipLoopError, ValueError, OSError) as exc:
            self.call_from_thread(self._on_run_failed, str(exc))
            return
        self.call_from_thread(self._on_run_done, output, opts["duration"])

    def _finish_run(self, message: str) -> None:
        elapsed = self._capture_elapsed()
        self._hide_run_progress()
        if elapsed is not None:
            message = f"{message} in {format_elapsed(elapsed)}"
        self._set_status(message)
        self.query_one("#run", Button).disabled = False
        self.query_one("#quit", Button).disabled = False

    def _on_run_failed(self, message: str) -> None:
        self._finish_run(message)

    def _on_run_done(self, output: Path, duration: float) -> None:
        self._finish_run(f"Wrote {output} ({duration:g}s target)")


def run_tui(
    *,
    initial_input: Path | None = None,
    initial_output: Path | None = None,
    initial_audio: Path | None = None,
) -> None:
    """Launch the interactive setup UI."""
    ClipLoopApp(
        initial_input=initial_input,
        initial_output=initial_output,
        initial_audio=initial_audio,
    ).run()
