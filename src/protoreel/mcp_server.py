"""Protoreel as an MCP server, so AI clients (Claude, Cursor, VS Code…) can film prototypes.

Start it with `protoreel mcp --folder ~/Prototypes`. Your MCP client launches this for you
once it is configured (see README.md); you never need to open a terminal.

Tools
-----
list_workspace   what can be recorded, plus recent takes and videos
record_video     film a prototype by following a script of clicks, drags and typing
render_take      film a take someone captured by hand in the Studio, in any format
preview_frame    a single PNG frame, to check framing and zoom before a full render
open_studio      open the Studio in the browser to capture a take by hand
check_setup      confirm Chromium and ffmpeg are ready
"""

from __future__ import annotations

import functools
import inspect
import json
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import Context, Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import HOMEPAGE, __version__
from .browser import install_chromium
from .encoder import find_ffmpeg, has_audio
from .renderer import RenderOptions, output_path, render, still
from .settings import FORMATS, RESOLUTIONS
from .studio.server import Studio
from .takes import Take
from .timeline import __doc__ as SCRIPT_GUIDE
from .workspace import Workspace

INSTRUCTIONS = f"""Protoreel films HTML prototypes into social-media videos (MP4) with a smooth on-screen cursor.

Typical flow:
1. list_workspace to see the prototypes (.html files) in the workspace folder.
2. preview_frame to check framing; raise `zoom` to make the prototype larger in frame.
3. record_video with a script that performs the interaction. Use CSS selectors from the
   prototype's HTML so clicks land on the right elements.
4. Tell the user where the video was saved. To re-cut a hand-made take, use render_take.

Formats: {", ".join(f"{f.key} ({f.use})" for f in FORMATS.values())}.
Resolutions: {", ".join(RESOLUTIONS)} (same framing, more pixels).

Script format
{SCRIPT_GUIDE}"""

# Problems the user can fix (a wrong file name, a bad option, a missing selector) are sent
# back to the AI client as readable messages instead of a generic "tool failed".
EXPECTED_ERRORS = (FileNotFoundError, ValueError, KeyError, RuntimeError)


def user_errors(tool):
    """Decorator: turn expected errors into ToolErrors with the original message."""
    if inspect.iscoroutinefunction(tool):

        @functools.wraps(tool)
        async def run_async(*args, **kwargs):
            try:
                return await tool(*args, **kwargs)
            except EXPECTED_ERRORS as error:
                raise ToolError(str(error)) from error

        return run_async

    @functools.wraps(tool)
    def run(*args, **kwargs):
        try:
            return tool(*args, **kwargs)
        except EXPECTED_ERRORS as error:
            raise ToolError(str(error)) from error

    return run


def build_server(workspace: Workspace, studio_port: int = 8765) -> MCPServer:
    """Create the MCP server for one workspace folder."""
    server = MCPServer(name="protoreel", version=__version__, instructions=INSTRUCTIONS, website_url=HOMEPAGE)
    studio = Studio(workspace, studio_port)

    def options_from(
        fmt: str,
        zoom: float,
        resolution: str,
        fps: int,
        cursor: bool,
        sound: bool,
        background: str | None,
        caption: str | None,
    ) -> RenderOptions:
        options = RenderOptions(
            format=fmt,
            zoom=zoom,
            resolution=resolution,
            fps=fps,
            cursor=cursor,
            sound=sound,
            background=background or None,
            caption=caption or None,
        )
        options.geometry()  # validates the values early, with a readable message
        return options

    def progress_reporter(ctx: Context):
        async def report(done: int, total: int | None):
            if done % 15 == 0 or done == total:
                await ctx.report_progress(done, total, f"Filming frame {done}" + (f" of {total}" if total else ""))

        return report

    # ------------------------------------------------------------ tools
    @server.tool(annotations=ToolAnnotations(read_only_hint=True))
    @user_errors
    def list_workspace() -> dict[str, Any]:
        """List the prototypes that can be recorded, plus recent takes and rendered videos."""
        renders = workspace.recent(workspace.renders, "*.mp4", 15)
        return {
            "folder": str(workspace.folder),
            "prototypes": [p.name for p in workspace.prototypes()],
            "takes": [p.name for p in workspace.recent(workspace.takes, "*.json", 15)],
            "renders": [
                {"file": str(p), "size_mb": round(p.stat().st_size / 1048576, 1), "sound": has_audio(p)}
                for p in renders
            ],
            "formats": {f.key: f"{f.width}x{f.height} · {f.use}" for f in FORMATS.values()},
        }

    @server.tool()
    @user_errors
    async def record_video(
        prototype: str,
        script: dict[str, Any] | str,
        format: str = "4x5",
        zoom: float = 2.0,
        resolution: str = "1080",
        fps: int = 60,
        cursor: bool = True,
        sound: bool = True,
        background: str | None = None,
        caption: str | None = None,
        output_name: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Film a prototype following a script, and save an MP4 in the workspace's renders/ folder.

        prototype: file name in the workspace (e.g. "checkout.html"), an absolute path, or an http(s) URL.
        script: {"start": POINT, "actions": [...]} - see the server instructions for every action.
          Example: {"actions": [{"wait": 400}, {"click": "#add", "dur": 700}, {"wait": 1200}]}
        format: 4x5 (feed), 9x16 (reels), 1x1, 16x9, 4x3 or 3x2 (Dribbble).
        zoom: 0.6-3.6. Higher makes the prototype bigger in frame (default 2).
        resolution: 1080, 2k, 3k or 4k. background: optional colour behind the page, e.g. "#ffffff".
        """
        if isinstance(script, str):
            script = json.loads(script)
        options = options_from(format, zoom, resolution, fps, cursor, sound, background, caption)
        source = prototype if prototype.startswith(("http://", "https://")) else workspace.find_prototype(prototype)
        out = output_path(workspace.renders, str(source), options, output_name)
        result = await render(source, script, options, out, progress_reporter(ctx) if ctx else None)
        return f"Saved {result.path}\n{result.summary()}"

    @server.tool()
    @user_errors
    async def render_take(
        take: str,
        format: str | None = None,
        zoom: float | None = None,
        resolution: str = "1080",
        fps: int = 60,
        cursor: bool = True,
        smooth: bool = True,
        sound: bool = True,
        background: str | None = None,
        caption: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Render a take that was captured by hand in the Studio (a .json file in takes/).

        Leave format and zoom empty to match how the take was captured, or pick another
        format to re-cut the same performance (the motion is re-centred in the new frame).
        """
        saved = Take.load(workspace.find_take(take))
        options = options_from(
            format or saved.format, zoom or saved.zoom, resolution, fps, cursor, sound, background, caption
        )
        options.smooth = smooth
        prototype = workspace.find_prototype(saved.page)
        out = output_path(workspace.renders, prototype.name, options)
        result = await render(prototype, saved, options, out, progress_reporter(ctx) if ctx else None)
        return f"Saved {result.path}\n{result.summary()}"

    @server.tool(annotations=ToolAnnotations(read_only_hint=True))
    @user_errors
    async def preview_frame(
        prototype: str,
        format: str = "4x5",
        zoom: float = 2.0,
        script: dict[str, Any] | str | None = None,
        at_ms: float | None = None,
        background: str | None = None,
    ) -> Image:
        """Return one frame as an image, exactly as it would appear in the video.

        Without a script you see the first frame. With a script you see the page after it
        has played (or after `at_ms` milliseconds of it). Use this to tune zoom and format.
        """
        if isinstance(script, str):
            script = json.loads(script)
        options = options_from(format, zoom, "1080", 60, True, False, background, None)
        source = prototype if prototype.startswith(("http://", "https://")) else workspace.find_prototype(prototype)
        png = await still(source, options, script, at_ms)
        return Image(data=png, format="png")

    @server.tool()
    @user_errors
    def open_studio(prototype: str | None = None) -> str:
        """Open the Protoreel Studio in the user's browser to capture a take by hand.

        Takes captured there are saved to takes/, so you can render them with render_take.
        """
        if prototype:
            prototype = workspace.find_prototype(prototype).name
        try:
            studio.serve_in_background()
        except OSError:
            pass  # the port is busy: almost always a Studio that is already running, so just open it
        return f"The Studio is open at {studio.open_in_browser(prototype)}"

    @server.tool()
    @user_errors
    async def check_setup(install_missing: bool = False) -> dict[str, str]:
        """Check that ffmpeg and Chromium are available. Set install_missing to download Chromium."""
        report = {"version": __version__, "workspace": str(workspace.folder)}
        try:
            report["ffmpeg"] = find_ffmpeg()
        except RuntimeError as error:
            report["ffmpeg"] = f"missing: {error}"
        report["chromium"] = await _chromium_status()
        if install_missing and report["chromium"] != "ready":
            install_chromium(quiet=True)
            report["chromium"] = await _chromium_status()
        return report

    return server


async def _chromium_status() -> str:
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as playwright:
            path = Path(playwright.chromium.executable_path)
        return "ready" if path.exists() else "not installed (call check_setup with install_missing=true)"
    except Exception as error:
        return f"unavailable: {error}"


def run(folder: str | None = None, studio_port: int = 8765) -> None:
    """Serve over stdio, the transport desktop MCP clients use."""
    build_server(Workspace.open(folder), studio_port).run("stdio")
