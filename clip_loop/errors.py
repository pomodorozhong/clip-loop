"""Shared exceptions for clip-loop."""


class ClipLoopError(Exception):
    """Validation or processing error for clip-loop."""

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        segment_index: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.segment_index = segment_index

    def __str__(self) -> str:
        return self.message
