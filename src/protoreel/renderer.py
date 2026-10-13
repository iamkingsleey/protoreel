"""The renderer: plays an interaction on a prototype and films it, one frame at a time.

How it works
------------
1. The prototype opens in headless Chromium with a *frozen clock* (page_scripts/clock.js).
2. For every video frame we apply that frame's pointer/keyboard input, advance the
   page's clock by exactly one frame (1/60 s), and take a screenshot.
3. Screenshots stream into ffmpeg, which writes the MP4.

Because time only moves when we say so, nothing can drop frames or stutter, no matter
how slow the machine is.
"""

from __future__ import annotations

import inspect
import math
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from . import page_scripts
from .audio import page_soundtrack
from .browser import launch
from .encoder import VideoEncoder, add_soundtrack
from .settings import (
    CURSOR_SCALE,
    DEFAULT_FORMAT,
    DEFAULT_FPS,
    DEFAULT_RESOLUTION,
    DEFAULT_ZOOM,
    LEAD_IN_MS,
    TAIL_MS,
    FrameGeometry,
    frame_geometry,
)
from .takes import Take, prepare_events
from .timeline import FrameInput, script_frames, take_frames
from .workspace import PrototypeServer

POINTERS = ("arrow", "touch")
WARM_UP_FRAMES = 30  # let entrance animations settle before filming starts
ProgressCallback = Callable[[int, int | None], object]  # (frames done, total if known); may be async


@dataclass
class RenderOptions:
    format: str = DEFAULT_FORMAT
    zoom: float = DEFAULT_ZOOM
    resolution: str = DEFAULT_RESOLUTION
    fps: int = DEFAULT_FPS
    cursor: bool = True
    pointer: str = "arrow"  # "arrow" (desktop) or "touch" (a fingertip dot, for mobile prototypes)
    smooth: bool = True  # smooth hand jitter in captured takes
    sound: bool = True
    background: str | None = None  # e.g. "#ffffff" — painted behind the page
    caption: str | None = None

    def geometry(self) -> FrameGeometry:
        if self.pointer not in POINTERS:
            raise ValueError(f"Unknown pointer '{self.pointer}'. Use {' or '.join(POINTERS)}.")
        return frame_geometry(self.format, float(self.zoom), self.resolution)


@dataclass
class RenderResult:
    path: Path
    frames: int
    seconds: float
    width: int
    height: int
    sound: str  # "added", "none" (page has no sound), "off", or a failure note

    def summary(self) -> str:
        sound = {"added": "with sound", "none": "silent (the page has no sound)", "off": "silent"}.get(
            self.sound, f"silent ({self.sound})"
        )
        return f"{self.path.name}: {self.width}x{self.height}, {self.seconds:.1f}s, {self.frames} frames, {sound}"


class Cancelled(Exception):
    """Raised when a render is cancelled part-way."""


def output_path(folder: Path, prototype: str, options: RenderOptions, name: str | None = None) -> Path:
    """renders/<page>_<format>_<resolution>_<timestamp>.mp4 (the Studio reads this pattern)."""
    if name:
        file = Path(name).name
        return folder / (file if file.lower().endswith(".mp4") else f"{file}.mp4")
    stem = Path(prototype).stem or "prototype"
    return folder / f"{stem}_{options.format}_{options.resolution}_{time.strftime('%Y%m%d-%H%M%S')}.mp4"


# ---------------------------------------------------------------- page session
@asynccontextmanager
async def open_page(prototype: Path | str, options: RenderOptions):
    """Open a prototype ready for filming and yield the Playwright page."""
    from playwright.async_api import async_playwright

    geometry = options.geometry()
    source = str(prototype)
    is_url = source.startswith(("http://", "https://"))
    server = None if is_url else PrototypeServer(Path(source).parent)
    try:
        if server:
            server.__enter__()
        url = source if is_url else server.url_for(Path(source))
        async with async_playwright() as playwright:
            browser = await launch(playwright)
            try:
                page = await browser.new_page(
                    viewport={"width": geometry.viewport_width, "height": geometry.viewport_height},
                    device_scale_factor=geometry.device_scale,
                )
                await page.add_init_script(page_scripts.clock())
                await page.goto(url, wait_until="load")
                await page.evaluate("document.fonts ? document.fonts.ready.then(() => true) : true")
                await page.evaluate(page_scripts.cursor(), [CURSOR_SCALE, options.pointer])
                await page.evaluate(page_scripts.decorations(), [options.caption or "", options.background or ""])
                frame_ms = 1000 / options.fps
                for _ in range(WARM_UP_FRAMES):
                    await page.evaluate("ms => window.__advance(ms)", frame_ms)
                yield page
            finally:
                await browser.close()
    finally:
        if server:
            server.__exit__(None, None, None)


def element_resolver(page, viewport_width: int, viewport_height: int):
    """Build the POINT resolver that scripts use (see timeline.py for the formats)."""

    async def resolve(point) -> tuple[float, float]:
        if isinstance(point, str):
            point = {"el": point}
        if isinstance(point, dict):
            selector = point.get("el") or point.get("selector")
            box = await page.evaluate(page_scripts.locate(), selector)
            if box is None:
                raise ValueError(f"No element matches the selector {selector!r}.")
            return box[0] + box[2] * float(point.get("x", 0.5)), box[1] + box[3] * float(point.get("y", 0.5))
        if isinstance(point, (list, tuple)) and len(point) == 2:

            def one(value, size):
                if isinstance(value, str) and value.strip().endswith("%"):
                    return float(value.strip()[:-1]) / 100 * size
                return float(value)

            return one(point[0], viewport_width), one(point[1], viewport_height)
        raise ValueError(
            f"Not a point: {point!r}. Use [x, y], ['50%', '50%'], '#selector' "
            "or {'el': '#selector', 'x': 0.5, 'y': 0.5}."
        )

    return resolve


class Player:
    """Applies FrameInputs to the page and steps its clock."""

    def __init__(self, page, options: RenderOptions):
        self.page = page
        self.options = options
        self.frame_ms = 1000 / options.fps
        self.position: tuple[float, float] | None = None
        self.pressed = False

    async def step(self, frame: FrameInput) -> None:
        page = self.page
        if self.position is None or (frame.x, frame.y) != self.position:
            await page.mouse.move(frame.x, frame.y)
            self.position = (frame.x, frame.y)
        if frame.down and not self.pressed:
            await page.mouse.down()
            self.pressed = True
        elif not frame.down and self.pressed:
            await page.mouse.up()
            self.pressed = False
        for key in frame.keys:
            await page.keyboard.press(key)
        if frame.text:
            await page.keyboard.type(frame.text)
        if frame.scroll != (0.0, 0.0):
            await page.evaluate(page_scripts.scroll(), [frame.x, frame.y, *frame.scroll])
        await page.evaluate(
            "([x, y, d, s, ms]) => { window.__cursor(x, y, d, s); window.__advance(ms); }",
            [frame.x, frame.y, frame.down or frame.touch, self.options.cursor, self.frame_ms],
        )


def frames_for_take(take: Take, options: RenderOptions) -> tuple[AsyncIterator[FrameInput], int]:
    geometry = options.geometry()
    events, duration = prepare_events(
        take, geometry.viewport_width, geometry.viewport_height, options.smooth, LEAD_IN_MS, TAIL_MS
    )
    total = max(1, math.ceil(duration * options.fps / 1000))
    return take_frames(events, duration, options.fps), total


# ---------------------------------------------------------------- public API
async def render(
    prototype: Path | str,
    interaction: Take | dict,
    options: RenderOptions,
    out: Path,
    on_progress: ProgressCallback | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> RenderResult:
    """Film `interaction` (a captured Take or a script dict) on `prototype` into `out`."""
    geometry = options.geometry()
    if isinstance(interaction, Take):
        interaction.validate()
    count = 0
    start_ms = 0.0
    sound_status = "off"
    try:
        with VideoEncoder(out, options.fps, geometry.video_width, geometry.video_height) as encoder:
            async with open_page(prototype, options) as page:
                if isinstance(interaction, Take):
                    frames, total = frames_for_take(interaction, options)
                else:
                    resolver = element_resolver(page, geometry.viewport_width, geometry.viewport_height)
                    frames, total = script_frames(interaction, resolver, options.fps, LEAD_IN_MS, TAIL_MS), None
                player = Player(page, options)
                start_ms = await page.evaluate("performance.now()")
                async for frame in frames:
                    await player.step(frame)
                    encoder.add_frame(await page.screenshot(type="png"))
                    count += 1
                    if on_progress:
                        reported = on_progress(count, total)
                        if inspect.isawaitable(reported):  # the MCP server reports progress asynchronously
                            await reported
                    if should_cancel and should_cancel():
                        raise Cancelled()
                if options.sound:
                    wav, sound_status = await page_soundtrack(page, start_ms + player.frame_ms, count * player.frame_ms)
    except BaseException:
        out.unlink(missing_ok=True)
        raise
    if options.sound and sound_status == "added" and not add_soundtrack(out, wav):
        sound_status = "failed: could not mix the sound into the video"
    return RenderResult(out, count, count / options.fps, geometry.video_width, geometry.video_height, sound_status)


async def still(
    prototype: Path | str, options: RenderOptions, script: dict | None = None, at_ms: float | None = None
) -> bytes:
    """One PNG frame: the page after `at_ms` of the script (or after the whole script).

    Handy for checking framing and zoom before committing to a full render.
    """
    geometry = options.geometry()
    async with open_page(prototype, options) as page:
        if script:
            resolver = element_resolver(page, geometry.viewport_width, geometry.viewport_height)
            player = Player(page, options)
            limit = None if at_ms is None else max(1, round(at_ms / 1000 * options.fps))
            done = 0
            async for frame in script_frames(script, resolver, options.fps, 0, 0):
                await player.step(frame)
                done += 1
                if limit and done >= limit:
                    break
        else:
            await page.evaluate("([x, y, d, s]) => window.__cursor(x, y, d, s)", [0, 0, False, False])
        return await page.screenshot(type="png")
