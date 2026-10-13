"""Turn an interaction into one input state per video frame.

There are two sources of interactions:

* a **take** — events captured by hand in the Studio (see takes.py)
* a **script** — a list of actions written by a person or an AI, e.g.
  ``{"start": ["50%", "80%"], "actions": [{"click": "#buy"}, {"wait": 800}]}``

Both become the same thing: an async stream of `FrameInput`, one per frame, which the
renderer applies to the page before capturing that frame.

Script actions (run in order)
-----------------------------
  {"wait": 500}                                  hold still for 500 ms
  {"move": POINT, "dur": 600, "ease": "smooth"}  glide the pointer to a point
  {"hover": POINT}                               same as move
  {"click": POINT, "dur": 500}                   glide to a point, then press and release
  {"click": true}                                press and release where the pointer is
  {"drag": {"to": POINT} | {"by": [dx, dy]}, "dur": 900}   press, move, release
  {"down": true} / {"up": true}                  press or release in place
  {"key": "Enter"}                               press one key (Playwright key names)
  {"type": "Hello", "delay": 70}                 type text, one character every 70 ms
  {"scroll": {"by": [0, 400]} | {"to": POINT}, "dur": 800}  scroll the page smoothly
  {"scroll": {"by": [0, 400]}, "swipe": true}    the same, with the pointer swiping like a finger

A POINT is any of:
  [x, y]                  CSS pixels in the viewport
  ["50%", "60%"]          a share of the viewport
  "#selector"             the centre of the first matching element
  {"el": "#selector", "x": 0.5, "y": 0.5}   a spot inside an element's box (0..1)

`dur` is in milliseconds. Eases: smooth (default, natural hand motion), linear, in, out, inout.
"""

from __future__ import annotations

import math
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field

Point = tuple[float, float]
Resolver = Callable[[object], Awaitable[Point]]  # turns a POINT into viewport coordinates

CLICK_HOLD_MS = 90  # how long a scripted click keeps the button down
DEFAULT_MOVE_MS = 600
DEFAULT_START = ["82%", "86%"]  # where the pointer rests before the first action


@dataclass
class FrameInput:
    """Everything the renderer does to the page for one frame."""

    x: float
    y: float
    down: bool
    keys: list[str] = field(default_factory=list)  # keys pressed this frame
    text: str = ""  # characters typed this frame
    scroll: Point = (0.0, 0.0)  # page scroll this frame, in CSS px
    touch: bool = False  # draw the pointer pressed without pressing the mouse (a finger swiping)


def ease(name: str, t: float) -> float:
    t = min(1.0, max(0.0, t))
    if name == "linear":
        return t
    if name == "in":
        return t**3
    if name == "out":
        return 1 - (1 - t) ** 3
    if name == "inout":
        return 4 * t**3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
    return t**3 * (t * (t * 6 - 15) + 10)  # "smooth": minimum-jerk, how hands move


def frames_for(ms: float, fps: int) -> int:
    """How many frames a duration lasts. Any positive duration lasts at least one frame."""
    return max(1, round(ms / 1000 * fps)) if ms > 0 else 0


# ---------------------------------------------------------------- takes
async def take_frames(events: list[dict], duration_ms: float, fps: int) -> AsyncIterator[FrameInput]:
    """Replay prepared take events (see takes.prepare_events) frame by frame."""
    frame_ms = 1000 / fps
    first = next((e for e in events if "x" in e), None)
    state = FrameInput(first["x"], first["y"], False) if first else FrameInput(0, 0, False)
    index = 0
    total = max(1, math.ceil(duration_ms / frame_ms))
    for k in range(total):
        now = k * frame_ms
        keys: list[str] = []
        while index < len(events) and events[index]["t"] <= now:
            e = events[index]
            index += 1
            if "x" in e:
                state.x, state.y = e["x"], e["y"]
            if e["type"] == "down":
                state.down = True
            elif e["type"] == "up":
                state.down = False
            elif e["type"] == "key":
                keys.append(e["key"])
        yield FrameInput(state.x, state.y, state.down, keys)


# ---------------------------------------------------------------- scripts
class ScriptError(ValueError):
    """A script action that cannot be understood."""


async def script_frames(
    script: dict, resolve: Resolver, fps: int, lead_in_ms: float, tail_ms: float
) -> AsyncIterator[FrameInput]:
    """Play a script, resolving element positions at the moment each action starts.

    Resolving late (rather than all up front) matters: earlier actions often open
    menus or move things, so an element's position is only known when we get there.
    """
    actions = script.get("actions")
    if not isinstance(actions, list):
        raise ScriptError('A script needs an "actions" list.')
    x, y = await resolve(script.get("start", DEFAULT_START))
    down = False

    def still(ms: float):
        return [FrameInput(x, y, down) for _ in range(frames_for(ms, fps))]

    for frame in still(lead_in_ms):
        yield frame

    for number, action in enumerate(actions, start=1):
        if not isinstance(action, dict) or not action:
            raise ScriptError(f'Action {number} should be an object like {{"wait": 500}}.')
        kind = next(iter(action))
        duration = float(action.get("dur", DEFAULT_MOVE_MS))
        curve = action.get("ease", "smooth")

        if kind == "wait":
            for frame in still(float(action["wait"])):
                yield frame

        elif kind in ("move", "hover"):
            target = await _target(action[kind], resolve, x, y)
            async for frame in _glide(x, y, target, duration, curve, down, fps):
                yield frame
            x, y = target

        elif kind == "click":
            spot = action["click"]
            if spot is not True:
                target = await resolve(spot)
                async for frame in _glide(x, y, target, duration, curve, down, fps):
                    yield frame
                x, y = target
            yield FrameInput(x, y, True)
            for frame in [FrameInput(x, y, True) for _ in range(frames_for(CLICK_HOLD_MS, fps) - 1)]:
                yield frame
            down = False
            yield FrameInput(x, y, False)

        elif kind == "drag":
            target = await _target(action["drag"], resolve, x, y)
            yield FrameInput(x, y, True)
            async for frame in _glide(x, y, target, duration if "dur" in action else 900, curve, True, fps):
                yield frame
            x, y = target
            yield FrameInput(x, y, False)
            down = False

        elif kind == "down":
            down = True
            yield FrameInput(x, y, down)

        elif kind == "up":
            down = False
            yield FrameInput(x, y, down)

        elif kind == "key":
            yield FrameInput(x, y, down, keys=[str(action["key"])])

        elif kind == "type":
            text = str(action["type"])
            gap = frames_for(float(action.get("delay", 70)), fps)
            for char in text:
                yield FrameInput(x, y, down, text=char)
                for _ in range(gap - 1):
                    yield FrameInput(x, y, down)

        elif kind == "scroll":
            travel = (0.0, 0.0)
            if action.get("swipe"):
                travel = await resolve(["0%", "32%"])  # how far a thumb travels: about a third of the screen
            async for frame in _scroll(
                action["scroll"], resolve, duration if "dur" in action else 800, curve, x, y, down, fps, travel[1]
            ):
                yield frame
                last = frame
            x, y = last.x, last.y

        else:
            raise ScriptError(
                f"Action {number} uses unknown step '{kind}'. "
                "Use wait, move, hover, click, drag, down, up, key, type or scroll."
            )

    for frame in still(tail_ms):
        yield frame


async def _target(spec, resolve: Resolver, x: float, y: float) -> Point:
    """`{"to": POINT}`, `{"by": [dx, dy]}` or a bare POINT."""
    if isinstance(spec, dict) and "by" in spec:
        dx, dy = spec["by"]
        return x + float(dx), y + float(dy)
    if isinstance(spec, dict) and "to" in spec:
        return await resolve(spec["to"])
    return await resolve(spec)


async def _glide(
    x: float, y: float, target: Point, duration: float, curve: str, down: bool, fps: int
) -> AsyncIterator[FrameInput]:
    steps = frames_for(duration, fps)
    tx, ty = target
    for i in range(1, steps + 1):
        k = ease(curve, i / steps)
        yield FrameInput(x + (tx - x) * k, y + (ty - y) * k, down)


async def _scroll(
    spec,
    resolve: Resolver,
    duration: float,
    curve: str,
    x: float,
    y: float,
    down: bool,
    fps: int,
    swipe: float = 0.0,
) -> AsyncIterator[FrameInput]:
    """Scroll by steps. With `swipe` (max thumb travel in px) the pointer moves against the
    scroll, pressed-looking, like a finger dragging the page."""
    if isinstance(spec, dict) and "by" in spec:
        dx, dy = (float(v) for v in spec["by"])
    else:
        # scroll so the target point ends up in the middle of the viewport
        point = spec["to"] if isinstance(spec, dict) and "to" in spec else spec
        tx, ty = await resolve(point)
        mid_x, mid_y = await resolve(["50%", "50%"])
        dx, dy = tx - mid_x, ty - mid_y
    steps = max(1, frames_for(duration, fps))
    thumb = -math.copysign(min(abs(dy), swipe), dy) if swipe and dy else 0.0
    done_x = done_y = 0.0
    for i in range(1, steps + 1):
        k = ease(curve, i / steps)
        step_x, step_y = dx * k - done_x, dy * k - done_y
        done_x, done_y = dx * k, dy * k
        yield FrameInput(x, y + thumb * k, down, scroll=(step_x, step_y), touch=bool(swipe) and i < steps)
