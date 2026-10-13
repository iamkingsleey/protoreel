"""Video encoding with ffmpeg.

Frames arrive as PNG bytes and are piped straight into ffmpeg, which writes an H.264
MP4 that plays everywhere (yuv420p, +faststart). If ffmpeg is not installed, the copy
bundled with the `imageio-ffmpeg` package is used, so no separate install is needed.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .settings import VIDEO_CRF


def find_ffmpeg() -> str:
    """Path to an ffmpeg binary: the system one if present, else the bundled one."""
    for candidate in (shutil.which("ffmpeg"), "/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"):
        if candidate and Path(candidate).exists():
            return candidate
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as error:  # pragma: no cover - only when both are missing
        raise RuntimeError(
            "ffmpeg was not found. Install it (macOS: brew install ffmpeg) "
            "or reinstall Protoreel so its bundled copy is available."
        ) from error


class VideoEncoder:
    """Context manager: `with VideoEncoder(path, fps, w, h) as enc: enc.add_frame(png)`."""

    def __init__(self, out: Path, fps: int, width: int, height: int, crf: int = VIDEO_CRF):
        self.out = out
        self._cmd = [
            find_ffmpeg(),
            "-v",
            "error",
            "-y",
            "-f",
            "image2pipe",
            "-framerate",
            str(fps),
            "-c:v",
            "png",
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "medium",
            "-crf",
            str(crf),
            "-vf",
            f"scale={width}:{height}:flags=lanczos",
            "-movflags",
            "+faststart",
            str(out),
        ]
        self._process: subprocess.Popen | None = None

    def __enter__(self) -> VideoEncoder:
        self.out.parent.mkdir(parents=True, exist_ok=True)
        self._process = subprocess.Popen(self._cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        return self

    def add_frame(self, png: bytes) -> None:
        assert self._process and self._process.stdin
        self._process.stdin.write(png)

    def __exit__(self, exc_type, *rest) -> None:
        assert self._process and self._process.stdin
        self._process.stdin.close()
        stderr = self._process.stderr.read().decode(errors="replace") if self._process.stderr else ""
        code = self._process.wait()
        if code != 0 and exc_type is None:
            raise RuntimeError(f"ffmpeg could not encode the video: {stderr.strip()[-400:]}")


def add_soundtrack(video: Path, wav: bytes) -> bool:
    """Lay a WAV soundtrack under a finished video (AAC, trimmed to the video's length)."""
    with tempfile.TemporaryDirectory() as tmp:
        sound = Path(tmp) / "sound.wav"
        sound.write_bytes(wav)
        muxed = Path(tmp) / f"muxed{video.suffix}"
        result = subprocess.run(
            [
                find_ffmpeg(),
                "-v",
                "error",
                "-y",
                "-i",
                str(video),
                "-i",
                str(sound),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(muxed),
            ]
        )
        if result.returncode != 0:
            return False
        shutil.move(str(muxed), str(video))
        return True


def has_audio(video: Path) -> bool:
    """Cheap check used by the renders list: MP4s with sound contain a 'soun' handler box."""
    with open(video, "rb") as handle:
        return b"soun" in handle.read(262144)
