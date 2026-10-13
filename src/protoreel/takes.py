"""Takes: interactions captured by hand in the Studio.

A take is a list of timestamped pointer and key events plus the viewport it was
captured in. Takes are saved as JSON in the workspace's `takes/` folder so they can
be rendered again later, in any format, by the Studio, the CLI or an AI client.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

SMOOTHING_SIGMA_MS = 22.0  # how much hand jitter the Gaussian smoothing removes


@dataclass
class Take:
    page: str  # prototype file name the take belongs to
    viewport_width: int
    viewport_height: int
    format: str = "4x5"
    zoom: float = 2.0
    events: list[dict] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        return self.events[-1]["t"] if self.events else 0.0

    # ---- reading and writing -------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict, page: str = "") -> Take:
        """Accepts both the saved-file shape and the Studio's in-browser shape."""
        return cls(
            page=data.get("page", page),
            viewport_width=int(data.get("viewport_width", data.get("vw", 0))),
            viewport_height=int(data.get("viewport_height", data.get("vh", 0))),
            format=data.get("format", data.get("size", "4x5")),
            zoom=float(data.get("zoom", 2.0)),
            events=list(data.get("events", [])),
        )

    @classmethod
    def load(cls, path: Path) -> Take:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def save(self, folder: Path) -> Path:
        folder.mkdir(parents=True, exist_ok=True)
        stem = Path(self.page).stem or "take"
        path = folder / f"{stem}_{time.strftime('%Y%m%d-%H%M%S')}.json"
        path.write_text(json.dumps(asdict(self), indent=1), encoding="utf-8")
        return path

    def validate(self) -> None:
        pointer = [e for e in self.events if e.get("type") in ("move", "down", "up")]
        if len(pointer) < 3:
            raise ValueError("This take has almost no pointer movement, so there is nothing to render.")


def prepare_events(
    take: Take, viewport_width: int, viewport_height: int, smooth: bool, lead_in_ms: float, tail_ms: float
) -> tuple[list[dict], float]:
    """Get a take ready to play back.

    * re-centres it when the video frame differs from the one it was captured in
    * optionally smooths hand jitter out of the pointer path
    * shifts time so playback starts after a short lead-in

    Returns the events and the total duration in milliseconds.
    """
    events = sorted((dict(e) for e in take.events), key=lambda e: e["t"])
    if not events:
        raise ValueError("The take is empty.")

    dx = (viewport_width - take.viewport_width) / 2
    dy = (viewport_height - take.viewport_height) / 2
    for e in events:
        if "x" in e:
            e["x"] += dx
            e["y"] += dy

    if smooth:
        _smooth_pointer_path([e for e in events if "x" in e])

    t0 = events[0]["t"]
    for e in events:
        e["t"] = e["t"] - t0 + lead_in_ms
    return events, events[-1]["t"] + tail_ms


def _smooth_pointer_path(points: list[dict]) -> None:
    """Gaussian-smooth x/y over time, in place. Presses and releases stay at their times."""
    sigma = SMOOTHING_SIGMA_MS
    smoothed = []
    for i, p in enumerate(points):
        total_w = sx = sy = 0.0
        j = i
        while j >= 0 and p["t"] - points[j]["t"] < 3 * sigma:
            j -= 1
        for q in points[j + 1 :]:
            dt = q["t"] - p["t"]
            if dt > 3 * sigma:
                break
            w = math.exp(-(dt * dt) / (2 * sigma * sigma))
            total_w += w
            sx += w * q["x"]
            sy += w * q["y"]
        smoothed.append((sx / total_w, sy / total_w))
    for p, (x, y) in zip(points, smoothed, strict=True):
        p["x"], p["y"] = x, y
