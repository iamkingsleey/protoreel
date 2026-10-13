"""Command line: `protoreel <command>`.

protoreel studio                 open the Studio (capture takes by hand, render them)
protoreel record PAGE SCRIPT     film a scripted interaction
protoreel render-take TAKE       film a take captured in the Studio
protoreel mcp                    run the MCP server (your AI client starts this for you)
protoreel setup                  download Chromium and print MCP client config
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
from pathlib import Path

from . import __version__
from .browser import install_chromium
from .encoder import find_ffmpeg
from .renderer import RenderOptions, output_path, render
from .settings import DEFAULT_FORMAT, DEFAULT_FPS, DEFAULT_RESOLUTION, DEFAULT_ZOOM, FORMATS, RESOLUTIONS
from .takes import Take
from .workspace import Workspace


def _add_folder(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--folder", help="workspace folder (default: $PROTOREEL_HOME or ~/Protoreel)")


def _add_video_options(parser: argparse.ArgumentParser, format_default: str | None = DEFAULT_FORMAT) -> None:
    parser.add_argument("--format", choices=list(FORMATS), default=format_default, help="video shape")
    parser.add_argument(
        "--zoom",
        type=float,
        default=None if format_default is None else DEFAULT_ZOOM,
        help="0.6–3.6; higher makes the prototype bigger in frame",
    )
    parser.add_argument("--res", choices=list(RESOLUTIONS), default=DEFAULT_RESOLUTION, help="export resolution")
    parser.add_argument("--fps", type=int, choices=(30, 60), default=DEFAULT_FPS)
    parser.add_argument("--no-cursor", action="store_true", help="hide the on-screen pointer")
    parser.add_argument("--no-sound", action="store_true", help="skip the prototype's own sound")
    parser.add_argument("--bg", help="background colour behind the page, e.g. '#ffffff'")
    parser.add_argument("--caption", help="small caption near the bottom of the frame")
    parser.add_argument("--out", help="output file name (saved in renders/)")


def _options(args, fmt: str, zoom: float) -> RenderOptions:
    return RenderOptions(
        format=fmt,
        zoom=zoom,
        resolution=args.res,
        fps=args.fps,
        cursor=not args.no_cursor,
        sound=not args.no_sound,
        background=args.bg,
        caption=args.caption,
    )


def _progress(done: int, total: int | None) -> None:
    if done % 10 == 0 or done == total:
        text = f"  frame {done}" + (f" of {total}" if total else "")
        print(f"\r{text}", end="", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- commands
def cmd_studio(args) -> None:
    from .studio.server import Studio

    studio = Studio(Workspace.open(args.folder), args.port)
    try:
        studio.start()
    except OSError:
        print(f"The Studio is already running at {studio.url}")
        if not args.no_browser:
            studio.open_in_browser()
        return
    print(f"Protoreel Studio is running at {studio.url}  (workspace: {studio.workspace.folder})")
    print("Press Ctrl+C or Quit in the app to stop.")
    if not args.no_browser:
        studio.open_in_browser()
    studio.serve_forever()


def cmd_record(args) -> None:
    workspace = Workspace.open(args.folder)
    page = args.page if args.page.startswith(("http://", "https://")) else workspace.find_prototype(args.page)
    script = json.loads(Path(args.script).read_text(encoding="utf-8"))
    options = _options(args, args.format, args.zoom)
    out = output_path(workspace.renders, str(page), options, args.out)
    result = asyncio.run(render(page, script, options, out, _progress))
    print(f"\nSaved {result.summary()}\n{result.path}")


def cmd_render_take(args) -> None:
    workspace = Workspace.open(args.folder)
    take = Take.load(workspace.find_take(args.take))
    options = _options(args, args.format or take.format, args.zoom or take.zoom)
    page = workspace.find_prototype(take.page)
    out = output_path(workspace.renders, page.name, options, args.out)
    result = asyncio.run(render(page, take, options, out, _progress))
    print(f"\nSaved {result.summary()}\n{result.path}")


def cmd_mcp(args) -> None:
    from .mcp_server import run

    run(args.folder, args.studio_port)


def cmd_setup(args) -> None:
    print(f"Protoreel {__version__}")
    print(f"ffmpeg:   {find_ffmpeg()}")
    print("Chromium: downloading if needed…")
    install_chromium()
    folder = str(Workspace.open(args.folder).folder)
    print(f"Workspace: {folder}\n")
    print(client_config(folder))


def client_config(folder: str) -> str:
    """Copy-paste snippets for the common MCP clients."""
    uvx = shutil.which("uvx") or "uvx"
    server = {"command": uvx, "args": ["protoreel", "mcp", "--folder", folder]}
    desktop = json.dumps({"mcpServers": {"protoreel": server}}, indent=2)
    return (
        "Claude Desktop / Cowork — add to claude_desktop_config.json:\n" + desktop + "\n\n"
        f'Claude Code:\n  claude mcp add protoreel -- uvx protoreel mcp --folder "{folder}"\n\n'
        'Cursor (.cursor/mcp.json) / VS Code (.vscode/mcp.json, key "servers"):\n'
        + json.dumps({"mcpServers": {"protoreel": server}}, indent=2)
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="protoreel", description="Turn HTML prototypes into social videos.")
    parser.add_argument("--version", action="version", version=f"protoreel {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    studio = commands.add_parser("studio", help="open the Studio web app")
    _add_folder(studio)
    studio.add_argument("--port", type=int, default=8765)
    studio.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    studio.set_defaults(run=cmd_studio)

    record = commands.add_parser("record", help="film a scripted interaction")
    record.add_argument("page", help="prototype file or http(s) URL")
    record.add_argument("script", help="JSON script (see examples/)")
    _add_folder(record)
    _add_video_options(record)
    record.set_defaults(run=cmd_record)

    take = commands.add_parser("render-take", help="film a take captured in the Studio")
    take.add_argument("take", help="take file name in takes/ or a path")
    _add_folder(take)
    _add_video_options(take, format_default=None)
    take.set_defaults(run=cmd_render_take)

    mcp = commands.add_parser("mcp", help="run the MCP server over stdio")
    _add_folder(mcp)
    mcp.add_argument("--studio-port", type=int, default=8765)
    mcp.set_defaults(run=cmd_mcp)

    setup = commands.add_parser("setup", help="install Chromium and print client config")
    _add_folder(setup)
    setup.set_defaults(run=cmd_setup)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        args.run(args)
    except (FileNotFoundError, ValueError) as error:
        sys.exit(f"protoreel: {error}")
