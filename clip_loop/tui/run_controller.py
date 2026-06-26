"""Run orchestration for the clip-loop TUI."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from clip_loop.errors import ClipLoopError
from clip_loop.options import ClipLoopOptions

if TYPE_CHECKING:
    from clip_loop.tui.run_progress import RunProgressController


class RunHost(Protocol):
    """App surface required to run clip-loop jobs."""

    def query_one(self, selector: str, expect_type: type): ...
    def call_from_thread(self, callback, *args) -> None: ...


class RunController:
    """Validates, persists, and runs clip-loop jobs from the TUI."""

    def __init__(
        self,
        host: RunHost,
        *,
        form,
        validator,
        progress: RunProgressController,
        runner,
        on_remember_last_run,
        on_set_status,
        on_clear_highlights,
        on_set_highlights,
        on_expand_sections,
    ) -> None:
        self._host = host
        self._form = form
        self._validator = validator
        self._progress = progress
        self._runner = runner
        self._remember_last_run = on_remember_last_run
        self._set_status = on_set_status
        self._clear_highlights = on_clear_highlights
        self._set_highlights = on_set_highlights
        self._expand_sections = on_expand_sections

    def start_run(self) -> ClipLoopOptions | None:
        from textual.widgets import Button

        result = self._validator.validate()
        if not result.ok:
            self._set_highlights(result.highlight_widget_ids)
            self._expand_sections(result.highlight_widget_ids)
            if result.highlight_widget_ids:
                self._host.query_one(result.highlight_widget_ids[0]).focus()
            self._set_status(result.error_message or "")
            return None

        self._clear_highlights()
        self._host.query_one("#run", Button).disabled = True
        self._host.query_one("#quit", Button).disabled = True
        self._set_status("")
        self._progress.show()
        options = self._form.collect()
        self._remember_last_run(options)
        return options

    def run_job_worker(self, options: ClipLoopOptions) -> None:
        try:
            output = self._runner(options)
        except ClipLoopError as exc:
            self._host.call_from_thread(self._on_run_failed, str(exc))
            return
        except (ValueError, OSError) as exc:
            self._host.call_from_thread(self._on_run_failed, str(exc))
            return
        self._host.call_from_thread(self._on_run_done, output, options.duration)

    def _on_run_failed(self, message: str) -> None:
        self._finish_run(message)

    def _on_run_done(self, output: Path, duration: float) -> None:
        self._finish_run(f"Wrote {output} ({duration:g}s target)")

    def _finish_run(self, message: str) -> None:
        from clip_loop.parsing import format_elapsed
        from textual.widgets import Button

        elapsed = self._progress.capture_elapsed()
        self._progress.hide()
        if elapsed is not None:
            message = f"{message} in {format_elapsed(elapsed)}"
        self._set_status(message)
        self._host.query_one("#run", Button).disabled = False
        self._host.query_one("#quit", Button).disabled = False
