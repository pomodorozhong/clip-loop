"""Read and parse clip-loop options from TUI widgets."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from textual.widgets import Checkbox, Input, Select, TabbedContent

from clip_loop.options import AudioSegment, ClipLoopOptions, VideoSegment
from clip_loop.parsing import parse_crop_corner, parse_duration
from clip_loop.tui.fields import (
    is_crop_enabled,
    ms_from_select,
    parse_duration_field,
    parse_keep_ratio,
    parse_speed,
)
from clip_loop.tui.constants import DURATION_PRESETS
from clip_loop.tui.segments import (
    AudioSegmentRows,
    VideoSegmentRows,
    set_keep_ratio_field,
    set_ms_field,
    set_speed_field,
)


class FormWidgets(Protocol):
    """Minimal widget query surface used by :class:`ClipLoopForm`."""

    def query_one(self, selector: str, expect_type: type): ...


class ClipLoopForm:
    """Reads :class:`~clip_loop.options.ClipLoopOptions` from the TUI form."""

    def __init__(self, app: FormWidgets) -> None:
        self._app = app
        self.video_rows = VideoSegmentRows(app)  # type: ignore[arg-type]
        self.audio_rows = AudioSegmentRows(app)  # type: ignore[arg-type]

    def video_mode_is_multiple(self) -> bool:
        tabs = self._app.query_one("#video-input-tabs", TabbedContent)
        return tabs.active == "video-multiple-tab"

    def audio_mode_is_multiple(self) -> bool:
        tabs = self._app.query_one("#audio-input-tabs", TabbedContent)
        return tabs.active == "audio-multiple-tab"

    def collect(self) -> ClipLoopOptions:
        output_text = self._app.query_one("#output-path", Input).value.strip()
        output_path = Path(output_text) if output_text else None

        if self.video_mode_is_multiple():
            video_segments = tuple(self.video_rows.read_segments())
        else:
            keep_ratio_select = self._app.query_one("#keep-ratio-preset", Select)
            keep_ratio: float | None = None
            crop_corner: str | None = None
            if is_crop_enabled(keep_ratio_select):
                keep_ratio = parse_keep_ratio(
                    keep_ratio_select,
                    self._app.query_one("#keep-ratio-custom", Input),
                )
                crop_corner = parse_crop_corner(
                    self._app.query_one("#crop-corner", Select).value
                )
            video_segments = (
                VideoSegment(
                    path=Path(self._app.query_one("#input-path", Input).value.strip()),
                    trim_start_ms=ms_from_select(
                        self._app.query_one("#trim-preset", Select),
                        self._app.query_one("#trim-custom", Input),
                    ),
                    speed_percent=parse_speed(
                        self._app.query_one("#speed-preset", Select),
                        self._app.query_one("#speed-custom", Input),
                    ),
                    keep_ratio=keep_ratio,
                    crop_corner=crop_corner,
                    alternate_reverse=self._app.query_one(
                        "#alternate-reverse", Checkbox
                    ).value,
                ),
            )

        if self.audio_mode_is_multiple():
            audio_segments = tuple(self.audio_rows.read_segments())
        else:
            audio_text = self._app.query_one("#audio-path", Input).value.strip()
            audio_segments = ()
            if audio_text:
                audio_segments = (
                    AudioSegment(
                        path=Path(audio_text),
                        trim_start_ms=ms_from_select(
                            self._app.query_one("#audio-trim-preset", Select),
                            self._app.query_one("#audio-trim-custom", Input),
                        ),
                        alternate_reverse=self._app.query_one(
                            "#audio-alternate-reverse", Checkbox
                        ).value,
                    ),
                )

        return ClipLoopOptions(
            video_segments=video_segments,
            duration=parse_duration_field(
                self._app.query_one("#duration-preset", Select),
                self._app.query_one("#duration-custom", Input),
            ),
            output_path=output_path,
            audio_segments=audio_segments,
            audio_crossfade_ms=ms_from_select(
                self._app.query_one("#crossfade-preset", Select),
                self._app.query_one("#crossfade-custom", Input),
            ),
            audio_gap_ms=ms_from_select(
                self._app.query_one("#gap-preset", Select),
                self._app.query_one("#gap-custom", Input),
            ),
            audio_seam_fade_ms=ms_from_select(
                self._app.query_one("#seam-fade-preset", Select),
                self._app.query_one("#seam-fade-custom", Input),
            ),
        )

    def duration_is_custom(self) -> bool:
        return self._app.query_one("#duration-preset", Select).value == "custom"

    def has_audio_path(self) -> bool:
        if self.audio_mode_is_multiple():
            return bool(self.audio_rows.read_segments())
        return bool(self._app.query_one("#audio-path", Input).value.strip())

    def browse_start_dir(self, input_id: str) -> Path:
        text = self._app.query_one(input_id, Input).value.strip() or "."
        start = Path(text)
        return start.parent if start.suffix else start

    def browse_save_defaults(self, input_id: str) -> tuple[Path, str]:
        text = self._app.query_one(input_id, Input).value.strip()
        if text:
            path = Path(text)
            if path.suffix:
                return path.parent, path.name
            return path, "output.mp4"
        input_text = self._app.query_one("#input-path", Input).value.strip()
        if input_text:
            source = Path(input_text)
            return source.parent, f"{source.stem}_looped{source.suffix or '.mp4'}"
        return Path.home(), "output.mp4"

    def sync_custom_visibility(self, preset_id: str, custom_id: str) -> None:
        select = self._app.query_one(f"#{preset_id}", Select)
        custom = self._app.query_one(f"#{custom_id}", Input)
        show = select.value == "custom"
        custom.display = show
        if not show:
            custom.value = ""

    def sync_crop_options(self) -> None:
        enabled = is_crop_enabled(self._app.query_one("#keep-ratio-preset", Select))
        custom = self._app.query_one("#keep-ratio-custom")
        corner = self._app.query_one("#crop-corner")
        custom.disabled = not enabled
        corner.disabled = not enabled
        if enabled:
            self.sync_custom_visibility("keep-ratio-preset", "keep-ratio-custom")
        else:
            custom.display = False

    def sync_audio_options(self) -> None:
        has_audio = self.has_audio_path()
        for selector in (
            "#audio-alternate-reverse",
            "#audio-trim-preset",
            "#audio-trim-custom",
            "#crossfade-preset",
            "#crossfade-custom",
            "#gap-preset",
            "#gap-custom",
            "#seam-fade-preset",
            "#seam-fade-custom",
        ):
            self._app.query_one(selector).disabled = not has_audio
        if has_audio:
            self._app.query_one("#media-options-tabs", TabbedContent).active = "media-audio-tab"

    async def apply(self, options: ClipLoopOptions) -> None:
        """Populate the form from a :class:`ClipLoopOptions` instance."""
        video_multiple = len(options.video_segments) > 1
        audio_multiple = len(options.audio_segments) > 1

        video_tabs = self._app.query_one("#video-input-tabs", TabbedContent)
        video_tabs.active = "video-multiple-tab" if video_multiple else "video-single-tab"

        audio_tabs = self._app.query_one("#audio-input-tabs", TabbedContent)
        audio_tabs.active = "audio-multiple-tab" if audio_multiple else "audio-single-tab"

        if video_multiple:
            await self.video_rows.apply_segments(list(options.video_segments))
        else:
            segment = options.video_segments[0]
            self._app.query_one("#input-path", Input).value = str(segment.path)
            self._set_ms_field("trim-preset", "trim-custom", segment.trim_start_ms)
            self._set_speed(segment.speed_percent)
            self._set_keep_ratio(segment.keep_ratio, segment.crop_corner)
            self._app.query_one("#alternate-reverse", Checkbox).value = (
                segment.alternate_reverse
            )

        self._app.query_one("#output-path", Input).value = (
            str(options.output_path) if options.output_path else ""
        )
        self._set_duration(options.duration)

        if audio_multiple:
            await self.audio_rows.apply_segments(list(options.audio_segments))
        else:
            if options.audio_segments:
                segment = options.audio_segments[0]
                self._app.query_one("#audio-path", Input).value = str(segment.path)
                self._set_ms_field(
                    "audio-trim-preset", "audio-trim-custom", segment.trim_start_ms
                )
                self._app.query_one("#audio-alternate-reverse", Checkbox).value = (
                    segment.alternate_reverse
                )
            else:
                self._app.query_one("#audio-path", Input).value = ""
                self._set_ms_field("audio-trim-preset", "audio-trim-custom", 0)
                self._app.query_one("#audio-alternate-reverse", Checkbox).value = False

        self._set_ms_field("crossfade-preset", "crossfade-custom", options.audio_crossfade_ms)
        self._set_ms_field("gap-preset", "gap-custom", options.audio_gap_ms)
        self._set_ms_field("seam-fade-preset", "seam-fade-custom", options.audio_seam_fade_ms)

    def _set_ms_field(self, preset_id: str, custom_id: str, ms: int) -> None:
        set_ms_field(self._app, f"#{preset_id}", f"#{custom_id}", ms)

    def _set_duration(self, duration: float) -> None:
        select = self._app.query_one("#duration-preset", Select)
        custom = self._app.query_one("#duration-custom", Input)
        for _, value in DURATION_PRESETS:
            if value == "custom":
                continue
            if parse_duration(value) == duration:
                select.value = value
                custom.value = ""
                return
        select.value = "custom"
        custom.value = _format_duration(duration)

    def _set_speed(self, speed_percent: float) -> None:
        set_speed_field(
            self._app, "#speed-preset", "#speed-custom", speed_percent
        )

    def _set_keep_ratio(
        self, keep_ratio: float | None, crop_corner: str | None
    ) -> None:
        set_keep_ratio_field(
            self._app,
            "#keep-ratio-preset",
            "#keep-ratio-custom",
            "#crop-corner",
            keep_ratio,
            crop_corner,
        )


def _format_duration(duration: float) -> str:
    if duration >= 3600 and duration % 3600 == 0:
        return f"{int(duration // 3600)}h"
    if duration >= 60 and duration % 60 == 0:
        return f"{int(duration // 60)}m"
    if duration == int(duration):
        return str(int(duration))
    return str(duration)
