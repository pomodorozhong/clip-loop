"""Event handlers mixin for the clip-loop TUI."""

from __future__ import annotations

import asyncio
import re
from dataclasses import replace
from pathlib import Path

from textual import on, work
from textual.widgets import Button, Input, Select, TabbedContent

from clip_loop.file_dialog import (
    AUDIO_EXTENSIONS,
    VIDEO_EXTENSIONS,
    native_file_dialog_available,
    pick_open_file,
    pick_save_file,
)
from clip_loop.pipeline import export_preview_video_clips
from clip_loop.tui.constants import AUDIO_SECTION_IDS, INVALID_CLASS, VIDEO_SECTION_IDS
from clip_loop.tui.segments import (
    sync_row_custom_visibility,
    sync_video_row_crop,
)
from clip_loop.tui.widgets import (
    AudioSegmentRow,
    FilePickScreen,
    PreviewPathScreen,
    VideoSegmentRow,
)


class FormHandlersMixin:
    """Preset visibility, browse dialogs, and segment row handlers."""

    @work(exclusive=True)
    async def _browse_into_input(
        self,
        input_id: str,
        start: Path,
        *,
        save: bool = False,
        audio: bool = False,
    ) -> None:
        if save:
            start_dir, default_name = self._form.browse_save_defaults(input_id)
            picked = await asyncio.to_thread(
                pick_save_file,
                title="Save output as",
                start=start_dir,
                default_name=default_name,
            )
        elif audio:
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

    @on(Select.Changed, "#resolution-preset")
    def resolution_preset_changed(self) -> None:
        self._form.sync_resolution_options()
        self._form.sync_custom_visibility("resolution-preset", "resolution-custom")

    @on(Select.Changed, "#trim-preset")
    def trim_preset_changed(self) -> None:
        self._form.sync_custom_visibility("trim-preset", "trim-custom")

    @on(Select.Changed, "#speed-preset")
    def speed_preset_changed(self) -> None:
        self._form.sync_custom_visibility("speed-preset", "speed-custom")

    @on(Select.Changed, "#audio-trim-preset")
    def audio_trim_preset_changed(self) -> None:
        self._form.sync_custom_visibility("audio-trim-preset", "audio-trim-custom")

    @on(Select.Changed, "#crossfade-preset")
    def crossfade_preset_changed(self) -> None:
        self._form.sync_custom_visibility("crossfade-preset", "crossfade-custom")

    @on(Select.Changed, "#gap-preset")
    def gap_preset_changed(self) -> None:
        self._form.sync_custom_visibility("gap-preset", "gap-custom")

    @on(Select.Changed, "#seam-fade-preset")
    def seam_fade_preset_changed(self) -> None:
        self._form.sync_custom_visibility("seam-fade-preset", "seam-fade-custom")

    @on(Select.Changed)
    def segment_select_changed(self, event: Select.Changed) -> None:
        select_id = event.select.id or ""
        if not select_id.startswith(("video-seg-", "audio-seg-")):
            return
        row = self._segment_row_ancestor(event.select, VideoSegmentRow)
        if select_id.endswith("-trim-preset"):
            sync_row_custom_visibility(
                event.select,
                f"#{select_id}",
                f"#{select_id.replace('-trim-preset', '-trim-custom')}",
            )
        elif select_id.endswith("-speed-preset"):
            sync_row_custom_visibility(
                event.select,
                f"#{select_id}",
                f"#{select_id.replace('-speed-preset', '-speed-custom')}",
            )
        elif select_id.endswith("-keep-ratio-preset"):
            sync_row_custom_visibility(
                event.select,
                f"#{select_id}",
                f"#{select_id.replace('-keep-ratio-preset', '-keep-ratio-custom')}",
            )
            if isinstance(row, VideoSegmentRow):
                sync_video_row_crop(row)

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
        self._browse_into_input(
            "#audio-path",
            self._form.browse_start_dir("#audio-path"),
            audio=True,
        )

    @on(Button.Pressed, "#add-video-segment")
    async def add_video_segment(self) -> None:
        await self._video_rows.add_row()

    @on(Button.Pressed, "#add-audio-segment")
    async def add_audio_segment(self) -> None:
        await self._audio_rows.add_row()

    @on(Button.Pressed, ".segment-remove")
    async def segment_remove_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        video_remove = re.fullmatch(r"video-seg-(\d+)-remove", button_id)
        if video_remove:
            index = int(video_remove.group(1))
            row = self.query_one(f"#video-seg-{index}-row", VideoSegmentRow)
            await self._video_rows.remove_row_widget(row)
            return
        audio_remove = re.fullmatch(r"audio-seg-(\d+)-remove", button_id)
        if audio_remove:
            index = int(audio_remove.group(1))
            row = self.query_one(f"#audio-seg-{index}-row", AudioSegmentRow)
            await self._audio_rows.remove_row_widget(row)

    @on(Button.Pressed)
    def segment_browse_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id.endswith("-remove"):
            return
        video_browse = re.fullmatch(r"video-seg-(\d+)-browse", button_id)
        if video_browse:
            index = int(video_browse.group(1))
            path_id = f"#video-seg-{index}-path"
            self._browse_into_input(
                path_id,
                self._form.browse_start_dir(path_id),
            )
            return
        audio_browse = re.fullmatch(r"audio-seg-(\d+)-browse", button_id)
        if audio_browse:
            index = int(audio_browse.group(1))
            path_id = f"#audio-seg-{index}-path"
            self._browse_into_input(
                path_id,
                self._form.browse_start_dir(path_id),
                audio=True,
            )

    @on(Button.Pressed, "#apply-last")
    @work
    async def apply_last_pressed(self) -> None:
        if self._last_run_options is None:
            return
        self._clear_validation_highlights()
        await self._form.apply(self._last_run_options)
        self._sync_form_visibility()
        self._set_status("Applied settings from last run.")

    @on(Button.Pressed, "#preview-clips")
    @work
    async def preview_clips_pressed(self) -> None:
        default_path = self._default_preview_path()
        preview_target = await self.push_screen_wait(PreviewPathScreen(default_path))
        if preview_target is None:
            return
        options = self._form.collect()
        options = replace(options, preview_output_path=preview_target)
        self._set_status("Creating preview clips...")
        self._preview_worker(options, preview_target)

    @work(thread=True, exclusive=True)
    def _preview_worker(self, options, preview_target: Path) -> None:
        try:
            preview_dir, outputs = export_preview_video_clips(
                options,
                base_output_path=preview_target,
            )
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Preview failed: {exc}")
            return
        self.call_from_thread(
            self._set_status,
            f"Created {len(outputs)} preview clip(s) in {preview_dir}",
        )

    def _default_preview_path(self) -> Path:
        output_text = self.query_one("#output-path", Input).value.strip()
        if output_text:
            return Path(output_text).expanduser()
        input_text = self.query_one("#input-path", Input).value.strip()
        if input_text:
            source = Path(input_text).expanduser()
            return source.parent / f"{source.stem}_looped{source.suffix or '.mp4'}"
        return Path.home() / "output.mp4"

    @on(Button.Pressed, "#quit")
    def quit_pressed(self) -> None:
        self.exit()

    def action_run(self) -> None:
        self.query_one("#run", Button).press()

    @on(Button.Pressed, "#run")
    def run_pressed(self) -> None:
        options = self._run_controller.start_run()
        if options is not None:
            self._run_job_worker(options)

    @work(thread=True, exclusive=True)
    def _run_job_worker(self, options) -> None:
        self._run_controller.run_job_worker(options)

    def _expand_sections_for(self, widget_ids: list[str]) -> None:
        if AUDIO_SECTION_IDS.intersection(widget_ids):
            self.query_one("#media-options-tabs", TabbedContent).active = "media-audio-tab"
        if VIDEO_SECTION_IDS.intersection(widget_ids):
            self.query_one("#media-options-tabs", TabbedContent).active = "media-video-tab"
            if not self._form.video_mode_is_multiple():
                self.query_one("#video-input-tabs", TabbedContent).active = "video-single-tab"

    def _segment_row_ancestor(self, widget, row_type: type):
        from clip_loop.tui.segments import segment_row_ancestor

        return segment_row_ancestor(widget, row_type)


def register_handler_mixin(app_cls: type, mixin_cls: type) -> None:
    """Merge @on handlers from a plain mixin into a Textual App subclass.

    Textual's metaclass only collects decorated handlers from the App class
    body. Methods on a non-MessagePump mixin are not registered automatically.
    """
    from textual.message import Message

    handlers: dict[
        type[Message], list[tuple]
    ] = app_cls.__dict__["_decorated_handlers"]
    for value in mixin_cls.__dict__.values():
        if callable(value) and hasattr(value, "_textual_on"):
            for message_type, selectors in value._textual_on:
                handlers.setdefault(message_type, []).append((value, selectors))
