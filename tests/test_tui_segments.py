"""Tests for clip_loop.tui.segments helpers."""

from __future__ import annotations

from clip_loop.tui.segments import set_keep_ratio_field, set_ms_field, set_speed_field
from tests.conftest import FakeInput, FakeSelect, FakeWidgetHost


def test_set_ms_field_preset() -> None:
    host = FakeWidgetHost(
        {
            "trim-preset": FakeSelect(),
            "trim-custom": FakeInput(),
        }
    )
    set_ms_field(host, "#trim-preset", "#trim-custom", 500)
    select = host.widgets["trim-preset"]
    custom = host.widgets["trim-custom"]
    assert isinstance(select, FakeSelect)
    assert isinstance(custom, FakeInput)
    assert select.value == "500"
    assert custom.value == ""


def test_set_ms_field_custom() -> None:
    host = FakeWidgetHost(
        {
            "trim-preset": FakeSelect(),
            "trim-custom": FakeInput(),
        }
    )
    set_ms_field(host, "#trim-preset", "#trim-custom", 750)
    select = host.widgets["trim-preset"]
    custom = host.widgets["trim-custom"]
    assert isinstance(select, FakeSelect)
    assert isinstance(custom, FakeInput)
    assert select.value == "custom"
    assert custom.value == "750"


def test_set_speed_field_preset() -> None:
    host = FakeWidgetHost(
        {
            "speed-preset": FakeSelect(),
            "speed-custom": FakeInput(),
        }
    )
    set_speed_field(host, "#speed-preset", "#speed-custom", 100.0)
    select = host.widgets["speed-preset"]
    assert isinstance(select, FakeSelect)
    assert select.value == "100"


def test_set_keep_ratio_field_disabled() -> None:
    host = FakeWidgetHost(
        {
            "keep-ratio-preset": FakeSelect(),
            "keep-ratio-custom": FakeInput(),
            "crop-corner": FakeSelect(),
        }
    )
    set_keep_ratio_field(
        host,
        "#keep-ratio-preset",
        "#keep-ratio-custom",
        "#crop-corner",
        None,
        None,
    )
    select = host.widgets["keep-ratio-preset"]
    assert isinstance(select, FakeSelect)
    assert select.value == "off"


def test_set_keep_ratio_field_custom() -> None:
    host = FakeWidgetHost(
        {
            "keep-ratio-preset": FakeSelect(),
            "keep-ratio-custom": FakeInput(),
            "crop-corner": FakeSelect(),
        }
    )
    set_keep_ratio_field(
        host,
        "#keep-ratio-preset",
        "#keep-ratio-custom",
        "#crop-corner",
        0.75,
        "bottom_right",
    )
    select = host.widgets["keep-ratio-preset"]
    custom = host.widgets["keep-ratio-custom"]
    corner = host.widgets["crop-corner"]
    assert isinstance(select, FakeSelect)
    assert isinstance(custom, FakeInput)
    assert isinstance(corner, FakeSelect)
    assert select.value == "custom"
    assert custom.value == "75%"
    assert corner.value == "bottom_right"
