# clip-loop

Loop a short video so the result matches a target length (default one hour). Uses [ffmpeg](https://ffmpeg.org/) under the hood.

## Requirements

- [uv](https://docs.astral.sh/uv/) (recommended) or another way to install the package
- **ffmpeg** on your `PATH` — install via your OS package manager or [ffmpeg.org](https://ffmpeg.org/download.html)

## Install

From the repository root:

```bash
uv sync --extra tui
```

This creates `.venv`, resolves dependencies from `uv.lock`, and installs the `clip-loop` command into that environment. The `tui` extra adds [Textual](https://textual.textualize.io/) for the interactive setup UI (`--tui`). For CLI-only use, `uv sync` without the extra is enough.

## Update

From the repository root:

```bash
git pull
uv sync
```

This updates the `clip-loop` to the latest version.

## Usage

```text
clip-loop [-h] [--tui] [-d DURATION] [-o PATH] [--alternate-reverse] [--trim-start-ms N] [--audio PATH] [--audio-alternate-reverse] [--audio-crossfade-ms N] [--audio-gap-ms N] [--audio-seam-fade-ms N] [input]
```

| Argument | Description |
|----------|-------------|
| `input` | Path to the source video file. |
| `-d`, `--duration` | Target length of the output. Default is **1 hour** (`1h`). |
| `-o`, `--output` | Output file path. Default is `<input_stem>_looped<suffix>` next to the input (e.g. `clip.mp4` → `clip_looped.mp4`). |
| `--alternate-reverse` | Ping-pong: play the clip forward, then backward, then repeat that pattern. Jumps at loop points are usually invisible on the picture (re-encodes once for the forward/back segment). |
| `--trim-start-ms N` | Drop the first **N** milliseconds of the file before any looping (default: 0). Uses input seek; with stream copy, the cut may align to the nearest keyframe, not an exact millisecond. |
| `--audio PATH` | Optional external audio file (for example MP3). Audio can be any length: it will be looped if too short or trimmed if too long so the output still matches target duration. |
| `--audio-alternate-reverse` | With `--audio`, make audio ping-pong (forward then reversed, then repeat). This is separate from `--alternate-reverse` so you can control audio reverse behavior independently. |
| `--audio-crossfade-ms N` | With `--audio`, crossfade stitched audio seams by **N** milliseconds (`0` disables crossfade). Applies whether or not `--audio-alternate-reverse` is used. |
| `--audio-gap-ms N` | With `--audio`, append **N** milliseconds of silence between stitched audio clips (`0` disables gap). Applies whether or not `--audio-alternate-reverse` is used. |
| `--audio-seam-fade-ms N` | With `--audio`, fade volume down near each clip end and up at each clip start by **N** milliseconds (`0` disables). Applies whether or not `--audio-alternate-reverse` is used. |
| `--tui` | Open an interactive terminal UI: duration and millisecond presets as dropdowns, booleans as checkboxes, **Video options** and **Audio options** in separate collapsible sections, and file browse buttons. Requires `uv sync --extra tui`. |

**Duration** can be:

- A number of **seconds** (e.g. `3600`)
- A value with a suffix: **`h`** (hours), **`m`** (minutes), or **`s`** (seconds), e.g. `1h`, `30m`, `90s`

Run the CLI through uv:

```bash
uv run clip-loop --tui
uv run clip-loop --tui path/to/clip.mp4
uv run clip-loop path/to/clip.mp4
uv run clip-loop path/to/clip.mp4 -d 30m
uv run clip-loop path/to/clip.mp4 -d 2h -o long.mp4
uv run clip-loop path/to/clip.mp4 --alternate-reverse -d 10m
uv run clip-loop path/to/clip.mp4 --trim-start-ms 500
uv run clip-loop path/to/clip.mp4 --audio path/to/music.mp3 -d 1h
uv run clip-loop path/to/clip.mp4 --audio path/to/music.mp3 --audio-alternate-reverse -d 1h
uv run clip-loop path/to/clip.mp4 --audio path/to/music.mp3 --audio-crossfade-ms 120 -d 1h
uv run clip-loop path/to/clip.mp4 --audio path/to/music.mp3 --audio-gap-ms 250 -d 1h
uv run clip-loop path/to/clip.mp4 --audio path/to/music.mp3 --audio-seam-fade-ms 120 -d 1h
```

After `uv sync`, you can also activate `.venv` and run `clip-loop` directly.

## How it works

**Default:** ffmpeg skips the start trim (if any), loops the rest of the file, and trims to your duration, using stream copy (`-c copy`) when possible for speed. If ffmpeg fails with copy, your source may need re-encoding; in that case you can run ffmpeg manually with different codec options.

**`--alternate-reverse`:** ffmpeg builds one cycle = full forward play + full reversed play (video reversed; audio reversed on the backward half), writes a short H.264/AAC file, then loops that file with stream copy to the target length. The first pass re-encodes so reverses are possible.
