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
clip-loop [-h] [--tui] [-d DURATION] [-o PATH] [--alternate-reverse] [--trim-start-ms N]
          [--speed PERCENT] [--keep-ratio RATIO] [--corner CORNER]
          [--video PATH] [--video-trim-start-ms N] [--video-speed PERCENT]
          [--video-keep-ratio RATIO] [--video-corner CORNER] [--video-alternate-reverse]
          [--audio PATH] [--audio-trim-start-ms N] [--audio-alternate-reverse]
          [--audio-crossfade-ms N] [--audio-gap-ms N] [--audio-seam-fade-ms N]
          [input]
```

| Argument | Description |
|----------|-------------|
| `input` | Path to a single source video (legacy mode). Cannot be combined with `--video`. |
| `-d`, `--duration` | Target length of the output. Default is **1 hour** (`1h`). |
| `-o`, `--output` | Output file path. Default is `<input_stem>_looped<suffix>` next to the first input. If the target path already exists, a timestamp is appended to avoid overwriting (e.g. `video_looped_20250626_143022.mp4`). |
| `--alternate-reverse` | With a single positional `input`, ping-pong that video. Use `--video-alternate-reverse` per `--video` in multi-clip mode. |
| `--trim-start-ms N` | With a single positional `input`, skip the first **N** ms. Use `--video-trim-start-ms` per `--video` in multi-clip mode. |
| `--speed PERCENT` | With a single positional `input`, playback speed. Use `--video-speed` per `--video` in multi-clip mode. |
| `--keep-ratio RATIO` | With a single positional `input`, crop a corner before looping. Requires `--corner`. Use `--video-keep-ratio` / `--video-corner` per `--video` in multi-clip mode. |
| `--corner CORNER` | Corner to remove with `--keep-ratio` on a single input: `top_left`, `top_right`, `bottom_left`, `bottom_right`. |
| `--video PATH` | Add a video clip to join (repeatable). Per-clip options follow each `--video PATH`. |
| `--video-trim-start-ms N` | Trim start for the current `--video` clip. |
| `--video-speed PERCENT` | Speed for the current `--video` clip. |
| `--video-keep-ratio RATIO` | Crop ratio for the current `--video` clip (requires `--video-corner`). |
| `--video-corner CORNER` | Crop corner for the current `--video` clip. |
| `--video-alternate-reverse` | Ping-pong the current `--video` clip before join. |
| `--audio PATH` | Add an external audio clip to join (repeatable). Replaces video audio after join. |
| `--audio-trim-start-ms N` | Trim start for the current `--audio` clip. |
| `--audio-alternate-reverse` | Ping-pong the current `--audio` clip before join. |
| `--audio-crossfade-ms N` | Crossfade loop seams on the joined external audio by **N** ms (`0` disables). |
| `--audio-gap-ms N` | Silence between loop iterations on the joined external audio (`0` disables). |
| `--audio-seam-fade-ms N` | Fade in/out at loop seams on the joined external audio (`0` disables). |
| `--tui` | Interactive terminal UI with **Single** / **Multiple** tabs for video and audio input. Requires `uv sync --extra tui`. |

**Duration** can be:

- A number of **seconds** (e.g. `3600`)
- A value with a suffix: **`h`** (hours), **`m`** (minutes), or **`s`** (seconds), e.g. `1h`, `30m`, `90s`

### Single clip (legacy)

```bash
uv run clip-loop --tui
uv run clip-loop path/to/clip.mp4
uv run clip-loop path/to/clip.mp4 -d 30m
uv run clip-loop path/to/clip.mp4 -d 2h -o long.mp4
uv run clip-loop path/to/clip.mp4 --alternate-reverse -d 10m
uv run clip-loop path/to/clip.mp4 --trim-start-ms 500
uv run clip-loop path/to/clip.mp4 --speed 80 -d 1h
uv run clip-loop path/to/clip.mp4 --keep-ratio 80% --corner top_left -d 1h
uv run clip-loop path/to/clip.mp4 --audio path/to/music.mp3 --audio-alternate-reverse -d 1h
uv run clip-loop path/to/clip.mp4 --audio path/to/music.mp3 --audio-crossfade-ms 120 -d 1h
```

### Multi-clip join

```bash
uv run clip-loop --video a.mp4 --video-trim-start-ms 200 --video-alternate-reverse \
  --video b.mp4 --video-speed 120 -d 1h

uv run clip-loop --video a.mp4 --video b.mp4 \
  --audio x.mp3 --audio-trim-start-ms 50 --audio-alternate-reverse \
  --audio y.mp3 --audio-crossfade-ms 120 -d 1h -o joined_looped.mp4
```

After `uv sync`, you can also activate `.venv` and run `clip-loop` directly.

## How it works

**Default:** Each video clip is preprocessed (trim, crop, speed, ping-pong as configured), joined if there are multiple clips, then looped to the target duration with stream copy when possible.

**Per-clip ping-pong:** `--alternate-reverse` / `--video-alternate-reverse` and `--audio-alternate-reverse` build a forward+reverse cycle for that clip before join. The joined result is then looped forward to the target length.

**External audio:** When `--audio` is provided, joined audio replaces the video's audio track. Loop-time seam options (`--audio-crossfade-ms`, `--audio-gap-ms`, `--audio-seam-fade-ms`) apply to the joined external audio.

**Multi-clip join:** Unlike codecs or resolutions are normalized with a single re-encode before looping.
