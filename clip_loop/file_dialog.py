"""Native OS file dialogs for the TUI."""

from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

VIDEO_EXTENSIONS = ("mp4", "mov", "mkv", "avi", "webm", "m4v")
AUDIO_EXTENSIONS = ("mp3", "wav", "m4a", "aac", "flac", "ogg", "opus")


def native_file_dialog_available() -> bool:
    """Return True when a native OS file dialog can be shown."""
    system = platform.system()
    if system == "Darwin":
        return shutil.which("osascript") is not None
    if system == "Linux":
        return shutil.which("zenity") is not None or shutil.which("kdialog") is not None
    try:
        import tkinter  # noqa: F401
    except ImportError:
        return False
    return True


def _escape_applescript(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _resolve_start(start: Path | None) -> Path:
    if start is None:
        return Path.home()
    candidate = start.expanduser()
    if candidate.is_file():
        candidate = candidate.parent
    if candidate.is_dir():
        return candidate
    parent = candidate.parent
    return parent if parent.is_dir() else Path.home()


def _macos_run(script: str) -> str | None:
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    path = result.stdout.strip()
    return path or None


def _macos_pick_open(
    title: str,
    start_dir: Path,
    extensions: tuple[str, ...] | None,
) -> Path | None:
    prompt = _escape_applescript(title)
    location = f' default location POSIX file "{_escape_applescript(str(start_dir))}"'
    type_clause = ""
    if extensions:
        type_list = ", ".join(f'"{ext}"' for ext in extensions)
        type_clause = f" of type {{{type_list}}}"
    script = (
        f'POSIX path of (choose file with prompt "{prompt}"{location}{type_clause})'
    )
    path = _macos_run(script)
    return Path(path) if path else None


def _macos_pick_save(title: str, start_dir: Path, default_name: str) -> Path | None:
    prompt = _escape_applescript(title)
    location = f' default location POSIX file "{_escape_applescript(str(start_dir))}"'
    name = _escape_applescript(default_name)
    script = (
        "POSIX path of (choose file name with prompt "
        f'"{prompt}"{location} default name "{name}")'
    )
    path = _macos_run(script)
    return Path(path) if path else None


def _linux_pick_open(title: str, start_dir: Path) -> Path | None:
    if shutil.which("zenity"):
        command = [
            "zenity",
            "--file-selection",
            f"--title={title}",
            f"--filename={start_dir}/",
        ]
    elif shutil.which("kdialog"):
        command = ["kdialog", "--getopenfilename", str(start_dir), f"{title}|*"]
    else:
        return None
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return None
    if result.returncode != 0:
        return None
    path = result.stdout.strip()
    return Path(path) if path else None


def _linux_pick_save(title: str, start_dir: Path, default_name: str) -> Path | None:
    default_path = start_dir / default_name
    if shutil.which("zenity"):
        command = [
            "zenity",
            "--file-selection",
            "--save",
            f"--title={title}",
            f"--filename={default_path}",
        ]
    elif shutil.which("kdialog"):
        command = [
            "kdialog",
            "--getsavefilename",
            str(default_path),
            f"{title}|*",
        ]
    else:
        return None
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return None
    if result.returncode != 0:
        return None
    path = result.stdout.strip()
    return Path(path) if path else None


def _tkinter_pick_open(
    title: str,
    start_dir: Path,
    extensions: tuple[str, ...] | None,
) -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    filetypes = [("All files", "*.*")]
    if extensions:
        pattern = " ".join(f"*.{ext}" for ext in extensions)
        label = ", ".join(f".{ext}" for ext in extensions)
        filetypes.insert(0, (label, pattern))
    try:
        picked = filedialog.askopenfilename(
            title=title,
            initialdir=str(start_dir),
            filetypes=filetypes,
        )
    finally:
        root.destroy()
    return Path(picked) if picked else None


def _tkinter_pick_save(title: str, start_dir: Path, default_name: str) -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        picked = filedialog.asksaveasfilename(
            title=title,
            initialdir=str(start_dir),
            initialfile=default_name,
            defaultextension=".mp4",
            filetypes=[("Video files", "*.mp4 *.mov *.mkv"), ("All files", "*.*")],
        )
    finally:
        root.destroy()
    return Path(picked) if picked else None


def pick_open_file(
    *,
    title: str = "Select file",
    start: Path | None = None,
    extensions: tuple[str, ...] | None = None,
) -> Path | None:
    """Open the system file picker for an existing file."""
    start_dir = _resolve_start(start)
    system = platform.system()

    if system == "Darwin":
        return _macos_pick_open(title, start_dir, extensions)
    if system == "Linux":
        if shutil.which("zenity") or shutil.which("kdialog"):
            return _linux_pick_open(title, start_dir)

    return _tkinter_pick_open(title, start_dir, extensions)


def pick_save_file(
    *,
    title: str = "Save as",
    start: Path | None = None,
    default_name: str = "output.mp4",
) -> Path | None:
    """Open the system save dialog."""
    start_dir = _resolve_start(start)
    system = platform.system()

    if system == "Darwin":
        return _macos_pick_save(title, start_dir, default_name)
    if system == "Linux":
        if shutil.which("zenity") or shutil.which("kdialog"):
            return _linux_pick_save(title, start_dir, default_name)

    return _tkinter_pick_save(title, start_dir, default_name)
