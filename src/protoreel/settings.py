"""Shared constants: video formats, export resolutions and render defaults.

Everything that describes *what* a video looks like lives here, so the renderer,
the Studio and the MCP server all agree on the same names.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VideoFormat:
    """A social-video frame size at 1080p-class resolution."""

    key: str  # short id used everywhere, e.g. "4x5"
    width: int  # pixels at the "1080" resolution
    height: int
    label: str  # "4:5"
    use: str  # where it is typically posted


FORMATS: dict[str, VideoFormat] = {
    f.key: f
    for f in [
        VideoFormat("4x5", 1080, 1350, "4:5", "Instagram / LinkedIn feed"),
        VideoFormat("9x16", 1080, 1920, "9:16", "Reels, TikTok, Shorts"),
        VideoFormat("1x1", 1080, 1080, "1:1", "Square"),
        VideoFormat("16x9", 1920, 1080, "16:9", "Landscape, YouTube, X"),
        VideoFormat("4x3", 1600, 1200, "4:3", "Dribbble"),
        VideoFormat("3x2", 1800, 1200, "3:2", "Dribbble wide"),
    ]
}

# Export resolutions scale the pixel count only. The page layout (and so the framing)
# stays exactly the same, which means one take looks identical at every resolution.
RESOLUTIONS: dict[str, float] = {"1080": 1.0, "2k": 4 / 3, "3k": 1.5, "4k": 2.0}

DEFAULT_FORMAT = "4x5"
DEFAULT_RESOLUTION = "1080"
DEFAULT_ZOOM = 2.0  # device pixel ratio: higher = the prototype looks bigger in frame
DEFAULT_FPS = 60
ZOOM_RANGE = (0.6, 3.6)
FPS_CHOICES = (30, 60)

LEAD_IN_MS = 500  # still frames before the first action
TAIL_MS = 700  # still frames after the last action
CURSOR_SCALE = 1.2
VIDEO_CRF = 16  # x264 quality; lower is sharper and bigger


def even(value: float) -> int:
    """Video encoders need even dimensions."""
    return int(round(value / 2)) * 2


@dataclass(frozen=True)
class FrameGeometry:
    """How big the page is laid out (CSS px) and how big the video is (px)."""

    viewport_width: int
    viewport_height: int
    video_width: int
    video_height: int
    device_scale: float


def frame_geometry(fmt: str, zoom: float, resolution: str) -> FrameGeometry:
    """Work out the viewport and output size for a format, zoom and resolution.

    The viewport is the format size divided by zoom, so at zoom 2 a 4:5 video lays the
    page out at 540 x 675 CSS pixels and renders it at 2x: sharp, and twice as large.
    """
    if fmt not in FORMATS:
        raise ValueError(f"Unknown format '{fmt}'. Choose one of: {', '.join(FORMATS)}")
    if resolution not in RESOLUTIONS:
        raise ValueError(f"Unknown resolution '{resolution}'. Choose one of: {', '.join(RESOLUTIONS)}")
    lo, hi = ZOOM_RANGE
    if not lo <= zoom <= hi:
        raise ValueError(f"Zoom must be between {lo} and {hi}")
    base = FORMATS[fmt]
    scale = RESOLUTIONS[resolution]
    return FrameGeometry(
        viewport_width=round(base.width / zoom),
        viewport_height=round(base.height / zoom),
        video_width=even(base.width * scale),
        video_height=even(base.height * scale),
        device_scale=zoom * scale,
    )
