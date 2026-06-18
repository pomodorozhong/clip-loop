"""Crop geometry (pure logic, no I/O)."""


def compute_crop_rect(
    width: int,
    height: int,
    keep_ratio: float,
    corner: str,
) -> tuple[int, int, int, int]:
    """Return crop_w, crop_h, x, y for the kept region (even dimensions)."""
    crop_w = int(width * keep_ratio)
    crop_h = int(height * keep_ratio)
    crop_w -= crop_w % 2
    crop_h -= crop_h % 2
    if crop_w <= 0 or crop_h <= 0:
        raise ValueError("keep ratio is too small for this video size")
    if crop_w > width or crop_h > height:
        raise ValueError("keep ratio must be at most 100%")

    if corner == "top_left":
        x = width - crop_w
        y = height - crop_h
    elif corner == "top_right":
        x = 0
        y = height - crop_h
    elif corner == "bottom_left":
        x = width - crop_w
        y = 0
    else:  # bottom_right
        x = 0
        y = 0
    return crop_w, crop_h, x, y
