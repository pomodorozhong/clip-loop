"""Run progress display for the clip-loop TUI."""

from __future__ import annotations

import time
from typing import Protocol

from textual.timer import Timer
from textual.widgets import Static

from clip_loop.parsing import format_elapsed


class ProgressHost(Protocol):
    """Widget query surface for run progress UI."""

    def query_one(self, selector: str, expect_type: type): ...
    def set_interval(self, interval: float, callback, *, name: str, pause: bool): ...


class RunProgressController:
    """Shows elapsed time while a clip-loop job runs."""

    def __init__(self, host: ProgressHost) -> None:
        self._host = host
        self._run_started: float | None = None
        self._run_timer: Timer | None = None

    def on_mount(self) -> None:
        self._run_timer = self._host.set_interval(
            0.25, self._update_run_timer, name="run_elapsed", pause=True
        )

    def show(self) -> None:
        self._run_started = time.perf_counter()
        self._host.query_one("#run-progress").add_class("visible")
        self._host.query_one("#run-timer", Static).update("Elapsed: 0s")
        self._update_run_timer()
        if self._run_timer is not None:
            self._run_timer.resume()

    def hide(self) -> None:
        self._host.query_one("#run-progress").remove_class("visible")
        self._run_started = None
        if self._run_timer is not None:
            self._run_timer.pause()

    def capture_elapsed(self) -> float | None:
        if self._run_started is None:
            return None
        return time.perf_counter() - self._run_started

    def _update_run_timer(self) -> None:
        if self._run_started is None:
            return
        elapsed = time.perf_counter() - self._run_started
        self._host.query_one("#run-timer", Static).update(
            f"Elapsed: {format_elapsed(elapsed)}"
        )
