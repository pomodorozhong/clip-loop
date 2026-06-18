"""Video encoding, looping, crop, and speed adjustment."""

from __future__ import annotations

from pathlib import Path

from clip_loop.crop import compute_crop_rect
from clip_loop.ffmpeg.executor import FfmpegExecutor
from clip_loop.ffmpeg.probe import MediaProbe
from clip_loop.parsing import default_crop_output_path
from clip_loop.validation import validate_crop_options


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


class VideoProcessor:
    """Video transformations via ffmpeg."""

    def __init__(self, executor: FfmpegExecutor, probe: MediaProbe) -> None:
        self._executor = executor
        self._probe = probe

    def build_forward_reverse_cycle(
        self,
        input_path: Path,
        cycle_path: Path,
        *,
        trim_start_sec: float = 0.0,
    ) -> None:
        """One play forward + one play backward; output length is 2× the source clip."""
        has_audio = self._probe.has_audio(input_path)
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
        self._executor.run(
            cmd,
            error_message=(
                "ffmpeg failed while building forward/reverse cycle. "
                "Check that the file is a supported video (and audio) format."
            ),
        )

    def stream_loop_copy(
        self,
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
        self._executor.run(
            cmd,
            error_message="ffmpeg failed while looping the cycle to the target duration.",
        )

    def simple_loop(
        self,
        input_path: Path,
        output_path: Path,
        duration_sec: float,
        *,
        trim_start_sec: float = 0.0,
    ) -> None:
        try:
            self.stream_loop_copy(
                input_path, output_path, duration_sec, trim_start_sec=trim_start_sec
            )
        except RuntimeError as exc:
            raise RuntimeError(
                "ffmpeg failed. Try re-encoding: some inputs need `-c` other than copy."
            ) from exc

    def crop(
        self,
        *,
        input_path: Path,
        keep_ratio: float,
        corner: str,
        output_path: Path | None = None,
    ) -> Path:
        """Crop away a corner, scale back to original size, and return the output path."""
        validate_crop_options(
            probe=self._probe,
            input_path=input_path,
            keep_ratio=keep_ratio,
            corner=corner,
        )
        width, height = self._probe.video_size(input_path)
        crop_w, crop_h, x, y = compute_crop_rect(width, height, keep_ratio, corner)
        resolved_output = (
            output_path if output_path else default_crop_output_path(input_path)
        )
        has_audio = self._probe.has_audio(input_path)
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
        self._executor.run(
            cmd,
            error_message=(
                "ffmpeg failed while cropping video. "
                "Check that the file is a supported video format."
            ),
        )
        return resolved_output

    def adjust_speed(
        self,
        input_path: Path,
        output_path: Path,
        speed_percent: float,
        *,
        trim_start_sec: float = 0.0,
    ) -> None:
        """Re-encode video (and embedded audio) at the given speed percentage."""
        speed_factor = speed_percent / 100.0
        setpts_factor = 1.0 / speed_factor
        has_audio = self._probe.has_audio(input_path)
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
        self._executor.run(
            cmd,
            error_message=(
                "ffmpeg failed while adjusting playback speed. "
                "Check that the file is a supported video format."
            ),
        )
