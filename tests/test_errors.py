"""Tests for clip_loop.errors."""

from __future__ import annotations

from clip_loop.errors import ClipLoopError


def test_clip_loop_error_attributes() -> None:
    exc = ClipLoopError(
        "something failed",
        field="duration",
        segment_index=2,
    )
    assert exc.message == "something failed"
    assert exc.field == "duration"
    assert exc.segment_index == 2
    assert str(exc) == "something failed"
