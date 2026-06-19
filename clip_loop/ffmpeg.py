"""ffmpeg/ffprobe subprocess helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        sys.stderr.write(
            "clip-loop requires ffmpeg in PATH. Install it from https://ffmpeg.org/\n"
        )
        sys.exit(1)


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_looped{input_path.suffix}")


def default_crop_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_cropped{input_path.suffix}")


def ffprobe_video_size(path: Path) -> tuple[int, int]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    value = r.stdout.strip()
    if not value or "x" not in value:
        raise ValueError(f"ffprobe could not determine video size: {path}")
    width_str, height_str = value.split("x", 1)
    return int(width_str), int(height_str)


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


def ffprobe_has_audio(path: Path) -> bool:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index",
        "-of",
        "csv=p=0",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return bool(r.stdout.strip())


def ffprobe_audio_duration_sec(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    value = r.stdout.strip()
    if not value:
        raise ValueError(f"ffprobe could not determine audio duration: {path}")
    return float(value)


def build_forward_reverse_cycle(
    input_path: Path,
    cycle_path: Path,
    *,
    has_audio: bool,
    trim_start_sec: float = 0.0,
) -> None:
    """One play forward + one play backward; output length is 2× the source clip."""
    head = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
    ]
    if trim_start_sec > 0:
        head.extend(["-ss", str(trim_start_sec)])
    if has_audio:
        filt = (
            "[0:v]split[v][vr];[vr]reverse[r];[v][r]concat=n=2:v=1:a=0[vout];"
            "[0:a]asplit[a][ar];[ar]areverse[arout];[a][arout]concat=n=2:v=0:a=1[aout]"
        )
        cmd = [
            *head,
            "-i",
            str(input_path),
            "-filter_complex",
            filt,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(cycle_path),
        ]
    else:
        filt = (
            "[0:v]split[v][vr];[vr]reverse[r];[v][r]concat=n=2:v=1:a=0[vout]"
        )
        cmd = [
            *head,
            "-i",
            str(input_path),
            "-filter_complex",
            filt,
            "-map",
            "[vout]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(cycle_path),
        ]
    subprocess.run(cmd, check=True)


def run_stream_loop_copy(
    input_path: Path,
    output_path: Path,
    duration_sec: float,
    *,
    trim_start_sec: float = 0.0,
) -> None:
    """Loop input with stream copy until duration_sec."""
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
    ]
    if trim_start_sec > 0:
        cmd.extend(["-ss", str(trim_start_sec)])
    cmd.extend(
        [
            "-stream_loop",
            "-1",
            "-i",
            str(input_path),
            "-t",
            str(duration_sec),
            "-c",
            "copy",
            str(output_path),
        ]
    )
    subprocess.run(cmd, check=True)


def run_simple_loop(
    input_path: Path,
    output_path: Path,
    duration_sec: float,
    *,
    trim_start_sec: float = 0.0,
) -> None:
    ensure_ffmpeg()
    try:
        run_stream_loop_copy(
            input_path, output_path, duration_sec, trim_start_sec=trim_start_sec
        )
    except subprocess.CalledProcessError:
        sys.stderr.write(
            "ffmpeg failed. Try re-encoding: some inputs need `-c` other than copy.\n"
        )
        sys.exit(1)


def apply_external_audio(
    video_path: Path, output_path: Path, audio_path: Path, duration_sec: float
) -> None:
    """Replace video audio with an external track, looping/trimming to duration."""
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-stream_loop",
        "-1",
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-t",
        str(duration_sec),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def build_forward_reverse_audio_cycle(audio_path: Path, cycle_path: Path) -> None:
    """Create one audio cycle: forward then reversed."""
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-filter_complex",
        "[0:a]asplit[a][ar];[ar]areverse[arout];[a][arout]concat=n=2:v=0:a=1[aout]",
        "-map",
        "[aout]",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(cycle_path),
    ]
    subprocess.run(cmd, check=True)


def build_crossfaded_audio_cycle(
    audio_path: Path, cycle_path: Path, *, crossfade_sec: float
) -> None:
    """Create one cycle with a crossfaded loop seam."""
    duration_sec = ffprobe_audio_duration_sec(audio_path)
    max_crossfade_sec = duration_sec * 0.49
    effective_crossfade_sec = min(crossfade_sec, max_crossfade_sec)
    if effective_crossfade_sec <= 0:
        raise ValueError("effective crossfade duration must be positive")

    filt = (
        f"[0:a][1:a]acrossfade=d={effective_crossfade_sec}:c1=tri:c2=tri[xf];"
        f"[xf]atrim=start={effective_crossfade_sec}:end={duration_sec + effective_crossfade_sec},"
        "asetpts=PTS-STARTPTS[aout]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-i",
        str(audio_path),
        "-filter_complex",
        filt,
        "-map",
        "[aout]",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(cycle_path),
    ]
    subprocess.run(cmd, check=True)


def build_gapped_audio_cycle(audio_path: Path, cycle_path: Path, *, gap_sec: float) -> None:
    """Create one cycle by appending silence to the end."""
    duration_sec = ffprobe_audio_duration_sec(audio_path)
    total_sec = duration_sec + gap_sec
    filt = f"[0:a]apad=pad_dur={gap_sec},atrim=end={total_sec},asetpts=PTS-STARTPTS[aout]"
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-filter_complex",
        filt,
        "-map",
        "[aout]",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(cycle_path),
    ]
    subprocess.run(cmd, check=True)


def build_seam_faded_audio_cycle(
    audio_path: Path, cycle_path: Path, *, fade_sec: float
) -> None:
    """Create one cycle with fade-in/out at both seam edges."""
    duration_sec = ffprobe_audio_duration_sec(audio_path)
    effective_fade_sec = min(fade_sec, duration_sec * 0.49)
    if effective_fade_sec <= 0:
        raise ValueError("effective seam fade duration must be positive")
    fade_out_start_sec = max(duration_sec - effective_fade_sec, 0.0)
    filt = (
        f"[0:a]afade=t=in:st=0:d={effective_fade_sec},"
        f"afade=t=out:st={fade_out_start_sec}:d={effective_fade_sec},"
        "asetpts=PTS-STARTPTS[aout]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-filter_complex",
        filt,
        "-map",
        "[aout]",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(cycle_path),
    ]
    subprocess.run(cmd, check=True)


def build_atempo_chain(speed_factor: float) -> str:
    """Build an atempo filter chain; each stage must stay within 0.5–2.0."""
    filters: list[str] = []
    remaining = speed_factor
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:g}")
    return ",".join(filters)


def run_speed_adjust(
    input_path: Path,
    output_path: Path,
    speed_percent: float,
    *,
    trim_start_sec: float = 0.0,
) -> None:
    """Re-encode video (and embedded audio) at the given speed percentage."""
    speed_factor = speed_percent / 100.0
    setpts_factor = 1.0 / speed_factor
    has_audio = ffprobe_has_audio(input_path)
    head = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
    ]
    if trim_start_sec > 0:
        head.extend(["-ss", str(trim_start_sec)])
    if has_audio:
        atempo = build_atempo_chain(speed_factor)
        filt = (
            f"[0:v]setpts={setpts_factor:g}*PTS[vout];"
            f"[0:a]{atempo}[aout]"
        )
        cmd = [
            *head,
            "-i",
            str(input_path),
            "-filter_complex",
            filt,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    else:
        cmd = [
            *head,
            "-i",
            str(input_path),
            "-vf",
            f"setpts={setpts_factor:g}*PTS",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        sys.stderr.write(
            "ffmpeg failed while adjusting playback speed. "
            "Check that the file is a supported video format.\n"
        )
        sys.exit(1)


def run_crop_video(
    *,
    input_path: Path,
    keep_ratio: float,
    corner: str,
    output_path: Path | None = None,
) -> Path:
    """Crop away a corner, scale back to original size, and return the output path."""
    from clip_loop.validation import validate_crop_options

    validate_crop_options(
        input_path=input_path,
        keep_ratio=keep_ratio,
        corner=corner,
    )
    ensure_ffmpeg()
    width, height = ffprobe_video_size(input_path)
    crop_w, crop_h, x, y = compute_crop_rect(width, height, keep_ratio, corner)
    resolved_output = output_path if output_path else default_crop_output_path(input_path)
    has_audio = ffprobe_has_audio(input_path)
    filt = f"crop={crop_w}:{crop_h}:{x}:{y},scale={width}:{height}"
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-vf",
        filt,
        "-map",
        "0:v:0",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
    ]
    if has_audio:
        cmd.extend(["-map", "0:a:0", "-c:a", "copy"])
    else:
        cmd.append("-an")
    cmd.append(str(resolved_output))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        sys.stderr.write(
            "ffmpeg failed while cropping video. "
            "Check that the file is a supported video format.\n"
        )
        sys.exit(1)
    return resolved_output


def _make_temp_audio_path() -> Path:
    fd, tmp_name = tempfile.mkstemp(suffix=".m4a", prefix="clip_loop_")
    os.close(fd)
    return Path(tmp_name)


def prepare_audio_source(
    external_audio_path: Path,
    *,
    audio_alternate_reverse: bool = False,
    audio_crossfade_sec: float = 0.0,
    audio_gap_sec: float = 0.0,
    audio_seam_fade_sec: float = 0.0,
) -> tuple[Path, list[Path]]:
    """Build a loopable audio cycle; return the source path and temps to clean up."""
    temp_paths: list[Path] = []
    audio_source_path = external_audio_path

    if audio_alternate_reverse:
        temp_audio_cycle_path = _make_temp_audio_path()
        temp_paths.append(temp_audio_cycle_path)
        build_forward_reverse_audio_cycle(external_audio_path, temp_audio_cycle_path)
        audio_source_path = temp_audio_cycle_path

    if audio_gap_sec > 0:
        temp_audio_gap_cycle_path = _make_temp_audio_path()
        temp_paths.append(temp_audio_gap_cycle_path)
        build_gapped_audio_cycle(
            audio_source_path,
            temp_audio_gap_cycle_path,
            gap_sec=audio_gap_sec,
        )
        audio_source_path = temp_audio_gap_cycle_path

    if audio_crossfade_sec > 0:
        temp_audio_crossfade_cycle_path = _make_temp_audio_path()
        temp_paths.append(temp_audio_crossfade_cycle_path)
        build_crossfaded_audio_cycle(
            audio_source_path,
            temp_audio_crossfade_cycle_path,
            crossfade_sec=audio_crossfade_sec,
        )
        audio_source_path = temp_audio_crossfade_cycle_path

    if audio_seam_fade_sec > 0:
        temp_audio_seam_fade_cycle_path = _make_temp_audio_path()
        temp_paths.append(temp_audio_seam_fade_cycle_path)
        build_seam_faded_audio_cycle(
            audio_source_path,
            temp_audio_seam_fade_cycle_path,
            fade_sec=audio_seam_fade_sec,
        )
        audio_source_path = temp_audio_seam_fade_cycle_path

    return audio_source_path, temp_paths


def cleanup_temp_paths(paths: list[Path]) -> None:
    for path in paths:
        path.unlink(missing_ok=True)
