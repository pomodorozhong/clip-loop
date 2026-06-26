"""ffmpeg/ffprobe subprocess helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise ClipLoopError(
            "clip-loop requires ffmpeg in PATH. Install it from https://ffmpeg.org/"
        )


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_looped{input_path.suffix}")


def unique_output_path(path: Path) -> Path:
    """Return path, or a timestamp-suffixed variant if it already exists."""
    if not path.exists():
        return path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = path.with_name(f"{path.stem}_{timestamp}{path.suffix}")
    counter = 0
    while candidate.exists():
        counter += 1
        candidate = path.with_name(f"{path.stem}_{timestamp}_{counter}{path.suffix}")
    return candidate


def default_crop_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_cropped{input_path.suffix}")


from clip_loop.errors import ClipLoopError
from clip_loop.media import compute_crop_rect, ffprobe_video_size, validate_crop_geometry
from clip_loop.parsing import FILL_MODES


def build_scale_filter(width: int, height: int, fill_mode: str) -> str:
    """Build an ffmpeg video filter that scales to width×height."""
    if fill_mode not in FILL_MODES:
        raise ValueError(f"fill mode must be one of: {', '.join(sorted(FILL_MODES))}")
    if fill_mode == "fit":
        return (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
        )
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}:(iw-ow)/2:(ih-oh)/2,setsar=1"
    )


def run_scale_video(
    input_path: Path,
    output_path: Path,
    width: int,
    height: int,
    *,
    fill_mode: str = "fit",
) -> None:
    """Re-encode video (and copy or pass through audio) to the target resolution."""
    ensure_ffmpeg()
    has_audio = ffprobe_has_audio(input_path)
    filt = build_scale_filter(width, height, fill_mode)
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
    cmd.append(str(output_path))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise ClipLoopError(
            "ffmpeg failed while scaling video. "
            "Check that the file is a supported video format."
        ) from exc


def scale_video_to_target(
    input_path: Path,
    *,
    target_resolution: tuple[int, int],
    fill_mode: str,
    suffix: str = ".mp4",
) -> tuple[Path, list[Path]]:
    """Scale one clip to the target resolution; return the path and temps to clean up."""
    width, height = target_resolution
    current_w, current_h = ffprobe_video_size(input_path)
    if (current_w, current_h) == (width, height):
        return input_path, []
    temp = _make_temp_video_path(suffix)
    run_scale_video(input_path, temp, width, height, fill_mode=fill_mode)
    return temp, [temp]


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
    except subprocess.CalledProcessError as exc:
        raise ClipLoopError(
            "ffmpeg failed. Try re-encoding: some inputs need `-c` other than copy."
        ) from exc


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
    except subprocess.CalledProcessError as exc:
        raise ClipLoopError(
            "ffmpeg failed while adjusting playback speed. "
            "Check that the file is a supported video format."
        ) from exc


def run_crop_video(
    *,
    input_path: Path,
    keep_ratio: float,
    corner: str,
    output_path: Path | None = None,
    trim_start_sec: float = 0.0,
) -> Path:
    """Crop away a corner, scale back to original size, and return the output path."""
    validate_crop_geometry(
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
    head = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
    ]
    if trim_start_sec > 0:
        head.extend(["-ss", str(trim_start_sec)])
    cmd = [
        *head,
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
    except subprocess.CalledProcessError as exc:
        raise ClipLoopError(
            "ffmpeg failed while cropping video. "
            "Check that the file is a supported video format."
        ) from exc
    return resolved_output


def _make_temp_audio_path() -> Path:
    fd, tmp_name = tempfile.mkstemp(suffix=".m4a", prefix="clip_loop_")
    os.close(fd)
    return Path(tmp_name)


def _make_temp_video_path(suffix: str = ".mp4") -> Path:
    fd, tmp_name = tempfile.mkstemp(suffix=suffix, prefix="clip_loop_")
    os.close(fd)
    return Path(tmp_name)


def trim_video_copy(input_path: Path, output_path: Path, trim_start_sec: float) -> None:
    """Copy video (and embedded audio) from a trim point to the end."""
    ensure_ffmpeg()
    head = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(trim_start_sec),
        "-i",
        str(input_path),
        "-c",
        "copy",
        str(output_path),
    ]
    subprocess.run(head, check=True)


def trim_audio_copy(input_path: Path, output_path: Path, trim_start_sec: float) -> None:
    """Copy audio from a trim point to the end."""
    ensure_ffmpeg()
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(trim_start_sec),
        "-i",
        str(input_path),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def preprocess_video_segment(segment) -> tuple[Path, list[Path]]:
    """Apply per-segment video transforms; return output path and temps to clean up."""
    from clip_loop.options import VideoSegment

    if not isinstance(segment, VideoSegment):
        raise TypeError(f"expected VideoSegment, got {type(segment)!r}")

    temps: list[Path] = []
    current = segment.path
    trim_sec = segment.trim_start_ms / 1000.0

    if segment.keep_ratio is not None and segment.crop_corner is not None:
        temp = _make_temp_video_path(current.suffix or ".mp4")
        temps.append(temp)
        run_crop_video(
            input_path=current,
            keep_ratio=segment.keep_ratio,
            corner=segment.crop_corner,
            output_path=temp,
            trim_start_sec=trim_sec,
        )
        current = temp
        trim_sec = 0.0

    if segment.speed_percent != 100.0:
        temp = _make_temp_video_path(current.suffix or ".mp4")
        temps.append(temp)
        run_speed_adjust(
            current,
            temp,
            segment.speed_percent,
            trim_start_sec=trim_sec,
        )
        current = temp
        trim_sec = 0.0
    elif trim_sec > 0:
        temp = _make_temp_video_path(current.suffix or ".mp4")
        temps.append(temp)
        trim_video_copy(current, temp, trim_sec)
        current = temp
        trim_sec = 0.0

    if segment.alternate_reverse:
        temp = _make_temp_video_path(current.suffix or ".mp4")
        temps.append(temp)
        build_forward_reverse_cycle(
            current,
            temp,
            has_audio=ffprobe_has_audio(current),
            trim_start_sec=trim_sec,
        )
        current = temp

    return current, temps


def preprocess_audio_segment(segment) -> tuple[Path, list[Path]]:
    """Apply per-segment audio transforms; return output path and temps to clean up."""
    from clip_loop.options import AudioSegment

    if not isinstance(segment, AudioSegment):
        raise TypeError(f"expected AudioSegment, got {type(segment)!r}")

    temps: list[Path] = []
    current = segment.path
    trim_sec = segment.trim_start_ms / 1000.0

    if trim_sec > 0:
        temp = _make_temp_audio_path()
        temps.append(temp)
        trim_audio_copy(current, temp, trim_sec)
        current = temp

    if segment.alternate_reverse:
        temp = _make_temp_audio_path()
        temps.append(temp)
        build_forward_reverse_audio_cycle(current, temp)
        current = temp

    return current, temps


def _ffprobe_video_duration_sec(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    value = r.stdout.strip()
    if not value:
        raise ValueError(f"ffprobe could not determine video duration: {path}")
    return float(value)


def concat_video_files(
    paths: list[Path],
    output_path: Path,
    *,
    uniform_size: tuple[int, int] | None = None,
) -> None:
    """Concatenate videos (re-encode) to a common size and codec."""
    if len(paths) < 2:
        raise ValueError("concat_video_files requires at least two inputs")
    ensure_ffmpeg()
    if uniform_size is not None:
        width, height = uniform_size
    else:
        width, height = ffprobe_video_size(paths[0])
    has_any_audio = any(ffprobe_has_audio(path) for path in paths)

    inputs: list[str] = []
    for path in paths:
        inputs.extend(["-i", str(path)])

    filter_parts: list[str] = []
    concat_inputs: list[str] = []
    for index, path in enumerate(paths):
        vlabel = f"v{index}"
        if uniform_size is not None:
            filter_parts.append(f"[{index}:v]setsar=1[{vlabel}]")
        else:
            filter_parts.append(
                f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1[{vlabel}]"
            )
        if has_any_audio:
            if ffprobe_has_audio(path):
                alabel = f"a{index}"
                filter_parts.append(
                    f"[{index}:a]aformat=sample_rates=48000:channel_layouts=stereo[{alabel}]"
                )
                concat_inputs.append(f"[{vlabel}][{alabel}]")
            else:
                duration = _ffprobe_video_duration_sec(path)
                alabel = f"a{index}"
                filter_parts.append(
                    f"anullsrc=r=48000:cl=stereo,atrim=0:{duration},asetpts=PTS-STARTPTS[{alabel}]"
                )
                concat_inputs.append(f"[{vlabel}][{alabel}]")
        else:
            concat_inputs.append(f"[{vlabel}]")

    n = len(paths)
    if has_any_audio:
        filt = ";".join(filter_parts)
        filt += f";{''.join(concat_inputs)}concat=n={n}:v=1:a=1[outv][outa]"
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            *inputs,
            "-filter_complex",
            filt,
            "-map",
            "[outv]",
            "-map",
            "[outa]",
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
        filt = ";".join(filter_parts)
        filt += f";{''.join(concat_inputs)}concat=n={n}:v=1:a=0[outv]"
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            *inputs,
            "-filter_complex",
            filt,
            "-map",
            "[outv]",
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
    subprocess.run(cmd, check=True)


def concat_audio_files(paths: list[Path], output_path: Path) -> None:
    """Concatenate audio files into one track."""
    if len(paths) < 2:
        raise ValueError("concat_audio_files requires at least two inputs")
    ensure_ffmpeg()
    inputs: list[str] = []
    for path in paths:
        inputs.extend(["-i", str(path)])

    filter_parts: list[str] = []
    concat_inputs: list[str] = []
    for index in range(len(paths)):
        label = f"a{index}"
        filter_parts.append(
            f"[{index}:a]aformat=sample_rates=48000:channel_layouts=stereo[{label}]"
        )
        concat_inputs.append(f"[{label}]")

    n = len(paths)
    filt = ";".join(filter_parts)
    filt += f";{''.join(concat_inputs)}concat=n={n}:v=0:a=1[outa]"
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        *inputs,
        "-filter_complex",
        filt,
        "-map",
        "[outa]",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def prepare_audio_source(
    external_audio_path: Path,
    *,
    audio_crossfade_sec: float = 0.0,
    audio_gap_sec: float = 0.0,
    audio_seam_fade_sec: float = 0.0,
) -> tuple[Path, list[Path]]:
    """Build a loopable audio cycle; return the source path and temps to clean up."""
    temp_paths: list[Path] = []
    audio_source_path = external_audio_path

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
