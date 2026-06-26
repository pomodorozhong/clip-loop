"""Dynamic segment rows for the clip-loop TUI."""

from __future__ import annotations

from pathlib import Path

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, Label, Select

from clip_loop.options import AudioSegment, VideoSegment
from clip_loop.parsing import parse_crop_corner, parse_keep_ratio
from clip_loop.tui.constants import (
    CROP_CORNER_PRESETS,
    KEEP_RATIO_PRESETS,
    MS_PRESETS,
    SPEED_PRESETS,
)
from clip_loop.tui.fields import is_crop_enabled, ms_from_select, try_parse_speed


class _CollapsibleSegmentRow(Vertical):
    """Reusable collapsible container used by segment rows."""

    ROW_PREFIX = ""
    TITLE_PREFIX = ""

    def __init__(self, index: int) -> None:
        super().__init__(classes="segment-row", id=f"{self.ROW_PREFIX}-{index}-row")
        self.index = index
        self.collapsed = False

    def _header(self) -> ComposeResult:
        prefix = f"{self.ROW_PREFIX}-{self.index}"
        with Horizontal(classes="segment-header"):
            yield Label("▼", classes="segment-toggle")
            yield Label(
                f"{self.TITLE_PREFIX} {self.index + 1}",
                classes="segment-title",
            )
            yield Button("Remove", id=f"{prefix}-remove", classes="segment-remove")

    def _content(self) -> ComposeResult:
        raise NotImplementedError

    def compose(self) -> ComposeResult:
        yield from self._header()
        with Vertical(classes="segment-content"):
            yield from self._content()

    def on_click(self, event: events.Click) -> None:
        widget = event.widget
        if not isinstance(widget, Widget):
            return
        if widget.has_class("segment-remove"):
            return
        if widget.has_class("segment-header") or widget.has_class("segment-title") or widget.has_class(
            "segment-toggle"
        ):
            self.toggle_collapse()

    def toggle_collapse(self) -> None:
        self.collapsed = not self.collapsed
        icon = self.query_one(".segment-toggle", Label)
        if self.collapsed:
            icon.update("▶")
            self.add_class("-collapsed")
        else:
            icon.update("▼")
            self.remove_class("-collapsed")


class VideoSegmentRow(_CollapsibleSegmentRow):
    """One video segment row in the Multiple tab."""

    ROW_PREFIX = "video-seg"
    TITLE_PREFIX = "Video"

    def _content(self) -> ComposeResult:
        prefix = f"{self.ROW_PREFIX}-{self.index}"
        with Horizontal(classes="field-row"):
            yield Input(placeholder="path/to/clip.mp4", id=f"{prefix}-path")
            yield Button("Browse…", id=f"{prefix}-browse")
        yield Label("Trim start", classes="field-label")
        yield Select(MS_PRESETS, id=f"{prefix}-trim-preset", value="0")
        yield Input(
            placeholder="milliseconds",
            id=f"{prefix}-trim-custom",
            classes="hidden-custom",
        )
        yield Label("Playback speed", classes="field-label")
        yield Select(SPEED_PRESETS, id=f"{prefix}-speed-preset", value="100")
        yield Input(
            placeholder="e.g. 80 or 120",
            id=f"{prefix}-speed-custom",
            classes="hidden-custom",
        )
        yield Label("Crop before loop", classes="field-label")
        yield Select(KEEP_RATIO_PRESETS, id=f"{prefix}-keep-ratio-preset", value="off")
        yield Input(
            placeholder="e.g. 75% or 0.75",
            id=f"{prefix}-keep-ratio-custom",
            classes="hidden-custom",
            disabled=True,
        )
        yield Label("Crop corner", classes="field-label")
        yield Select(
            CROP_CORNER_PRESETS,
            id=f"{prefix}-crop-corner",
            value="top_left",
            disabled=True,
        )
        yield Checkbox("Ping-pong video", id=f"{prefix}-alternate-reverse")


class AudioSegmentRow(_CollapsibleSegmentRow):
    """One audio segment row in the Multiple tab."""

    ROW_PREFIX = "audio-seg"
    TITLE_PREFIX = "Audio"

    def _content(self) -> ComposeResult:
        prefix = f"{self.ROW_PREFIX}-{self.index}"
        with Horizontal(classes="field-row"):
            yield Input(placeholder="path/to/audio.mp3", id=f"{prefix}-path")
            yield Button("Browse…", id=f"{prefix}-browse")
        yield Label("Trim start", classes="field-label")
        yield Select(MS_PRESETS, id=f"{prefix}-trim-preset", value="0")
        yield Input(
            placeholder="milliseconds",
            id=f"{prefix}-trim-custom",
            classes="hidden-custom",
        )
        yield Checkbox("Ping-pong audio", id=f"{prefix}-alternate-reverse")


class VideoSegmentRows:
    LIST_ID = "#video-segments-list"

    def __init__(self, app: Widget) -> None:
        self._app = app
        self._next_index = 0

    @property
    def count(self) -> int:
        return len(self._rows())

    def _rows(self) -> list[VideoSegmentRow]:
        container = self._app.query_one(self.LIST_ID, Vertical)
        return list(container.query(VideoSegmentRow))

    def ensure_initial_rows(self, *, count: int = 2) -> None:
        while self.count < count:
            self.add_row()

    def add_row(self) -> int:
        index = self._next_index
        self._next_index += 1
        container = self._app.query_one(self.LIST_ID, Vertical)
        container.mount(VideoSegmentRow(index))
        self._sync_remove_buttons()
        return index

    def remove_row_widget(self, row: VideoSegmentRow) -> None:
        if self.count <= 1:
            return
        row.remove()
        self._sync_remove_buttons()

    def _sync_remove_buttons(self) -> None:
        disable_remove = self.count <= 1
        for row in self._rows():
            row.query_one(".segment-remove", Button).disabled = disable_remove

    async def clear_rows(self) -> None:
        container = self._app.query_one(self.LIST_ID, Vertical)
        await container.remove_children(VideoSegmentRow)
        self._next_index = 0

    def read_segments(self) -> list[VideoSegment]:
        segments: list[VideoSegment] = []
        for row in self._rows():
            prefix = f"video-seg-{row.index}"
            path_text = row.query_one(f"#{prefix}-path", Input).value.strip()
            if not path_text:
                continue
            trim_select = row.query_one(f"#{prefix}-trim-preset", Select)
            trim_custom = row.query_one(f"#{prefix}-trim-custom", Input)
            speed_select = row.query_one(f"#{prefix}-speed-preset", Select)
            speed_custom = row.query_one(f"#{prefix}-speed-custom", Input)
            keep_ratio_select = row.query_one(f"#{prefix}-keep-ratio-preset", Select)
            keep_ratio_custom = row.query_one(f"#{prefix}-keep-ratio-custom", Input)
            corner_select = row.query_one(f"#{prefix}-crop-corner", Select)

            keep_ratio: float | None = None
            crop_corner: str | None = None
            if is_crop_enabled(keep_ratio_select):
                keep_ratio = keep_ratio_from_form(keep_ratio_select, keep_ratio_custom)
                crop_corner = parse_crop_corner(corner_select.value)

            speed_percent, _ = try_parse_speed(speed_select, speed_custom)
            if speed_percent is None:
                speed_percent = 100.0

            segments.append(
                VideoSegment(
                    path=Path(path_text),
                    trim_start_ms=ms_from_select(trim_select, trim_custom),
                    speed_percent=speed_percent,
                    keep_ratio=keep_ratio,
                    crop_corner=crop_corner,
                    alternate_reverse=row.query_one(
                        f"#{prefix}-alternate-reverse", Checkbox
                    ).value,
                )
            )
        return segments

    async def apply_segments(self, segments: list[VideoSegment]) -> None:
        await self.clear_rows()
        if not segments:
            self.ensure_initial_rows()
            return
        for segment in segments:
            self.add_row()
            row = self._rows()[-1]
            prefix = f"video-seg-{row.index}"
            row.query_one(f"#{prefix}-path", Input).value = str(segment.path)
            set_ms_field(row, f"#{prefix}-trim-preset", f"#{prefix}-trim-custom", segment.trim_start_ms)
            set_speed_field(row, f"#{prefix}-speed-preset", f"#{prefix}-speed-custom", segment.speed_percent)
            set_keep_ratio_field(
                row,
                f"#{prefix}-keep-ratio-preset",
                f"#{prefix}-keep-ratio-custom",
                f"#{prefix}-crop-corner",
                segment.keep_ratio,
                segment.crop_corner,
            )
            row.query_one(f"#{prefix}-alternate-reverse", Checkbox).value = (
                segment.alternate_reverse
            )


class AudioSegmentRows:
    LIST_ID = "#audio-segments-list"

    def __init__(self, app: Widget) -> None:
        self._app = app
        self._next_index = 0

    @property
    def count(self) -> int:
        return len(self._rows())

    def _rows(self) -> list[AudioSegmentRow]:
        container = self._app.query_one(self.LIST_ID, Vertical)
        return list(container.query(AudioSegmentRow))

    def ensure_initial_rows(self, *, count: int = 2) -> None:
        while self.count < count:
            self.add_row()

    def add_row(self) -> int:
        index = self._next_index
        self._next_index += 1
        container = self._app.query_one(self.LIST_ID, Vertical)
        container.mount(AudioSegmentRow(index))
        self._sync_remove_buttons()
        return index

    def remove_row_widget(self, row: AudioSegmentRow) -> None:
        if self.count <= 1:
            return
        row.remove()
        self._sync_remove_buttons()

    def _sync_remove_buttons(self) -> None:
        disable_remove = self.count <= 1
        for row in self._rows():
            row.query_one(".segment-remove", Button).disabled = disable_remove

    async def clear_rows(self) -> None:
        container = self._app.query_one(self.LIST_ID, Vertical)
        await container.remove_children(AudioSegmentRow)
        self._next_index = 0

    def read_segments(self) -> list[AudioSegment]:
        segments: list[AudioSegment] = []
        for row in self._rows():
            prefix = f"audio-seg-{row.index}"
            path_text = row.query_one(f"#{prefix}-path", Input).value.strip()
            if not path_text:
                continue
            trim_select = row.query_one(f"#{prefix}-trim-preset", Select)
            trim_custom = row.query_one(f"#{prefix}-trim-custom", Input)
            segments.append(
                AudioSegment(
                    path=Path(path_text),
                    trim_start_ms=ms_from_select(trim_select, trim_custom),
                    alternate_reverse=row.query_one(
                        f"#{prefix}-alternate-reverse", Checkbox
                    ).value,
                )
            )
        return segments

    async def apply_segments(self, segments: list[AudioSegment]) -> None:
        await self.clear_rows()
        if not segments:
            self.ensure_initial_rows()
            return
        for segment in segments:
            self.add_row()
            row = self._rows()[-1]
            prefix = f"audio-seg-{row.index}"
            row.query_one(f"#{prefix}-path", Input).value = str(segment.path)
            set_ms_field(row, f"#{prefix}-trim-preset", f"#{prefix}-trim-custom", segment.trim_start_ms)
            row.query_one(f"#{prefix}-alternate-reverse", Checkbox).value = (
                segment.alternate_reverse
            )


def keep_ratio_from_form(select: Select[str], custom: Input) -> float:
    value = select.value
    if value is Select.BLANK or value == "off":
        raise ValueError("crop is disabled")
    if value == "custom":
        text = custom.value.strip() or "80%"
        return parse_keep_ratio(text)
    return parse_keep_ratio(value)


def set_ms_field(host: Widget, preset_id: str, custom_id: str, ms: int) -> None:
    select = host.query_one(preset_id, Select)
    custom = host.query_one(custom_id, Input)
    preset_values = {value for _, value in MS_PRESETS if value != "custom"}
    if str(ms) in preset_values:
        select.value = str(ms)
        custom.value = ""
        return
    select.value = "custom"
    custom.value = str(ms)


def set_speed_field(host: Widget, preset_id: str, custom_id: str, speed_percent: float) -> None:
    select = host.query_one(preset_id, Select)
    custom = host.query_one(custom_id, Input)
    if speed_percent == int(speed_percent):
        speed_text = str(int(speed_percent))
    else:
        speed_text = str(speed_percent)
    preset_values = {value for _, value in SPEED_PRESETS if value != "custom"}
    if speed_text in preset_values:
        select.value = speed_text
        custom.value = ""
        return
    select.value = "custom"
    custom.value = speed_text


def set_keep_ratio_field(
    host: Widget,
    preset_id: str,
    custom_id: str,
    corner_id: str,
    keep_ratio: float | None,
    crop_corner: str | None,
) -> None:
    select = host.query_one(preset_id, Select)
    custom = host.query_one(custom_id, Input)
    corner = host.query_one(corner_id, Select)
    if keep_ratio is None:
        select.value = "off"
        custom.value = ""
        corner.value = "top_left"
        custom.disabled = True
        corner.disabled = True
        return
    for _, value in KEEP_RATIO_PRESETS:
        if value in ("off", "custom"):
            continue
        if abs(parse_keep_ratio(value) - keep_ratio) < 1e-9:
            select.value = value
            custom.value = ""
            corner.value = crop_corner or "top_left"
            custom.disabled = False
            corner.disabled = False
            return
    select.value = "custom"
    custom.value = f"{keep_ratio * 100:g}%"
    corner.value = crop_corner or "top_left"
    custom.disabled = False
    corner.disabled = False


def segment_row_ancestor(widget: Widget | None, row_type: type) -> Widget | None:
    """Walk parents until a segment row widget is found."""
    while widget is not None and not isinstance(widget, row_type):
        widget = widget.parent  # type: ignore[assignment]
    return widget


def sync_video_row_crop(row: VideoSegmentRow) -> None:
    prefix = f"video-seg-{row.index}"
    select = row.query_one(f"#{prefix}-keep-ratio-preset", Select)
    enabled = is_crop_enabled(select)
    custom = row.query_one(f"#{prefix}-keep-ratio-custom", Input)
    corner = row.query_one(f"#{prefix}-crop-corner", Select)
    custom.disabled = not enabled
    corner.disabled = not enabled
    if enabled and select.value == "custom":
        custom.display = True
    elif not enabled:
        custom.display = False


def sync_row_custom_visibility(host: Widget, preset_id: str, custom_id: str) -> None:
    row = segment_row_ancestor(host, VideoSegmentRow) or segment_row_ancestor(host, AudioSegmentRow) or host
    select = row.query_one(preset_id, Select)
    custom = row.query_one(custom_id, Input)
    show = select.value == "custom"
    custom.display = show
    if not show:
        custom.value = ""
