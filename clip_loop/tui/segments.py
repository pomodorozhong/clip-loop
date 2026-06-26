"""Dynamic segment row managers for the clip-loop TUI."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, Select

from clip_loop.options import AudioSegment, VideoSegment
from clip_loop.parsing import parse_crop_corner
from clip_loop.tui.constants import KEEP_RATIO_PRESETS, MS_PRESETS, SPEED_PRESETS
from clip_loop.tui.fields import (
    is_crop_enabled,
    ms_from_select,
    parse_keep_ratio,
    try_parse_speed,
)
from clip_loop.tui.widgets.audio_segment_row import AudioSegmentRow
from clip_loop.tui.widgets.video_segment_row import VideoSegmentRow

RowT = TypeVar("RowT", bound=Widget)
SegmentT = TypeVar("SegmentT")


class SegmentRowsManager(ABC, Generic[RowT, SegmentT]):
    """Shared lifecycle for dynamic segment row lists."""

    LIST_ID: str
    ROW_CLASS: type[RowT]

    def __init__(self, app: Widget) -> None:
        self._app = app
        self._next_index = 0

    @property
    def count(self) -> int:
        return len(self._rows())

    def _rows(self) -> list[RowT]:
        from textual.containers import Vertical

        container = self._app.query_one(self.LIST_ID, Vertical)
        return list(container.query(self.ROW_CLASS))

    async def ensure_initial_rows(self, *, count: int = 2) -> None:
        while self.count < count:
            await self.add_row()

    async def add_row(self) -> int:
        index = self._next_index
        self._next_index += 1
        from textual.containers import Vertical

        container = self._app.query_one(self.LIST_ID, Vertical)
        await container.mount(self.ROW_CLASS(index))
        self._sync_remove_buttons()
        self._sync_row_labels()
        return index

    async def remove_row_widget(self, row: RowT) -> None:
        if self.count <= 1:
            return
        await row.remove()
        self._sync_remove_buttons()
        self._sync_row_labels()

    def _sync_remove_buttons(self) -> None:
        disable_remove = self.count <= 1
        for row in self._rows():
            row.query_one(".segment-remove", Button).disabled = disable_remove

    def _sync_row_labels(self) -> None:
        for position, row in enumerate(self._rows()):
            row.update_display_number(position)

    async def clear_rows(self) -> None:
        from textual.containers import Vertical

        container = self._app.query_one(self.LIST_ID, Vertical)
        await container.remove_children(self.ROW_CLASS)
        self._next_index = 0

    @abstractmethod
    def read_segments(self) -> list[SegmentT]:
        ...

    @abstractmethod
    async def apply_segments(self, segments: list[SegmentT]) -> None:
        ...


class VideoSegmentRows(SegmentRowsManager[VideoSegmentRow, VideoSegment]):
    LIST_ID = "#video-segments-list"
    ROW_CLASS = VideoSegmentRow

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
                keep_ratio = parse_keep_ratio(keep_ratio_select, keep_ratio_custom)
                crop_corner = parse_crop_corner(corner_select.value)

            speed_percent, _ = try_parse_speed(
                speed_select, speed_custom, id_prefix=prefix
            )
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
            await self.ensure_initial_rows()
            return
        for segment in segments:
            await self.add_row()
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


class AudioSegmentRows(SegmentRowsManager[AudioSegmentRow, AudioSegment]):
    LIST_ID = "#audio-segments-list"
    ROW_CLASS = AudioSegmentRow

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
            await self.ensure_initial_rows()
            return
        for segment in segments:
            await self.add_row()
            row = self._rows()[-1]
            prefix = f"audio-seg-{row.index}"
            row.query_one(f"#{prefix}-path", Input).value = str(segment.path)
            set_ms_field(row, f"#{prefix}-trim-preset", f"#{prefix}-trim-custom", segment.trim_start_ms)
            row.query_one(f"#{prefix}-alternate-reverse", Checkbox).value = (
                segment.alternate_reverse
            )


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
    from clip_loop.parsing import parse_keep_ratio as parse_ratio

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
        if abs(parse_ratio(value) - keep_ratio) < 1e-9:
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
