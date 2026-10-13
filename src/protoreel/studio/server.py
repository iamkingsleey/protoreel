"""The Studio: a local web app for capturing takes by hand and rendering them.

Open it with `protoreel studio`, or ask your AI client to call the `open_studio` tool.
It serves a single page (static/index.html) plus a small JSON API:

    GET  /                    the app
    GET  /api/files           prototypes and recent renders
    GET  /api/job/<id>        render progress
    GET  /proto/<file>        a prototype, for the preview iframe
    GET  /renders/<file>      a finished video (supports Range for scrubbing)
    POST /api/upload          add a dropped .html file to the workspace
    POST /api/takes           save a captured take to takes/
    POST /api/render          start rendering a take
    POST /api/cancel/<id>     stop a render
    POST /api/reveal          show a render in Finder (macOS)
    POST /api/quit            stop the Studio
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from urllib.parse import unquote, urlparse

from .. import page_scripts
from ..encoder import has_audio
from ..renderer import Cancelled, RenderOptions, output_path, render
from ..takes import Take
from ..workspace import Workspace, read_for_browser, safe_join

DEFAULT_PORT = 8765


class Jobs:
    """Background renders, polled by the UI."""

    def __init__(self):
        self._jobs: dict[str, dict] = {}

    def get(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> None:
        if job_id in self._jobs:
            self._jobs[job_id]["cancel"] = True

    def start(self, workspace: Workspace, request: dict) -> str:
        job_id = uuid.uuid4().hex[:8]
        job = {"id": job_id, "state": "starting", "frame": 0, "total": 0}
        self._jobs[job_id] = job
        threading.Thread(target=self._run, args=(job, workspace, request), daemon=True).start()
        return job_id

    @staticmethod
    def _run(job: dict, workspace: Workspace, request: dict) -> None:
        options = RenderOptions(
            format=request["size"],
            zoom=float(request["zoom"]),
            resolution=request.get("res", "1080"),
            fps=int(request["fps"]),
            cursor=bool(request.get("cursor", True)),
            smooth=bool(request.get("smooth", True)),
            sound=bool(request.get("sound", True)),
            background=request.get("bg") or None,
            caption=request.get("caption") or None,
        )
        prototype = workspace.find_prototype(request["page"])
        take = Take.from_dict(request["take"], page=request["page"])
        out = output_path(workspace.renders, prototype.name, options)
        job.update(state="rendering", out=out.name)

        def progress(done: int, total: int | None) -> None:
            job["frame"], job["total"] = done, total or done

        try:
            result = asyncio.run(render(prototype, take, options, out, progress, lambda: job.get("cancel", False)))
            job.update(state="done", sound=result.sound)
        except Cancelled:
            job["state"] = "cancelled"
        except Exception as error:
            job.update(state="error", error=str(error))


def ui_html() -> bytes:
    page = resources.files(__package__).joinpath("static/index.html").read_text(encoding="utf-8")
    return page.replace("/*__BG_FN__*/", page_scripts.background_function()).encode()


def make_handler(workspace: Workspace, jobs: Jobs, on_quit):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        # ---- helpers
        def send(self, code: int, body=b"", ctype: str = "application/json", headers: dict | None = None):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def json_body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(length) or b"{}")

        # ---- GET
        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                return self.send(200, ui_html(), "text/html; charset=utf-8")
            if path == "/api/files":
                renders = [
                    {"name": f.name, "mtime": f.stat().st_mtime, "bytes": f.stat().st_size, "sound": has_audio(f)}
                    for f in workspace.recent(workspace.renders, "*.mp4", 40)
                ]
                takes = [f.name for f in workspace.recent(workspace.takes, "*.json", 40)]
                return self.send(
                    200,
                    {
                        "protos": [p.name for p in workspace.prototypes()],
                        "renders": renders,
                        "takes": takes,
                        "folder": str(workspace.folder),
                    },
                )
            if path.startswith("/api/job/"):
                job = jobs.get(path.rsplit("/", 1)[-1])
                return self.send(200 if job else 404, job or {"error": "no such job"})
            if path.startswith("/proto/"):
                file = safe_join(workspace.folder, path[len("/proto/") :])
                if not file or not file.is_file():
                    return self.send(404, "not found", "text/plain")
                data, ctype = read_for_browser(file)
                return self.send(200, data, ctype)
            if path.startswith("/renders/"):
                return self.send_video(workspace.renders / Path(unquote(path[len("/renders/") :])).name)
            self.send(404, "not found", "text/plain")

        def send_video(self, file: Path):
            if not file.is_file():
                return self.send(404, "not found", "text/plain")
            size = file.stat().st_size
            wanted = self.headers.get("Range")
            if wanted and wanted.startswith("bytes="):
                first, _, last = wanted[6:].partition("-")
                start, end = int(first or 0), min(int(last) if last else size - 1, size - 1)
                with open(file, "rb") as handle:
                    handle.seek(start)
                    chunk = handle.read(end - start + 1)
                return self.send(
                    206, chunk, "video/mp4", {"Content-Range": f"bytes {start}-{end}/{size}", "Accept-Ranges": "bytes"}
                )
            return self.send(200, file.read_bytes(), "video/mp4", {"Accept-Ranges": "bytes"})

        # ---- POST
        def do_POST(self):
            path = urlparse(self.path).path
            if path == "/api/upload":
                return self.send(200, {"name": save_upload(workspace, self.json_body())})
            if path == "/api/takes":
                body = self.json_body()
                take = Take.from_dict(body.get("take", {}), page=body.get("page", ""))
                return self.send(200, {"name": take.save(workspace.takes).name})
            if path == "/api/render":
                request = self.json_body()
                if not request.get("take", {}).get("events"):
                    return self.send(400, {"error": "no take"})
                return self.send(200, {"id": jobs.start(workspace, request)})
            if path.startswith("/api/cancel/"):
                jobs.cancel(path.rsplit("/", 1)[-1])
                return self.send(200, {"ok": True})
            if path == "/api/reveal":
                reveal(workspace, self.json_body().get("name", ""))
                return self.send(200, {"ok": True})
            if path == "/api/quit":
                self.send(200, {"ok": True})
                threading.Thread(target=on_quit, daemon=True).start()
                return
            self.send(404, {"error": "not found"})

    return Handler


def save_upload(workspace: Workspace, body: dict) -> str:
    """Write a dropped prototype into the workspace without overwriting a different file."""
    name = Path(body.get("name", "prototype.html")).name
    if not name.lower().endswith(".html"):
        name += ".html"
    content = body.get("content", "")
    dest = workspace.folder / name
    if dest.exists() and dest.read_text(errors="replace") != content:
        number = 2
        while (workspace.folder / f"{dest.stem}-{number}.html").exists():
            number += 1
        dest = workspace.folder / f"{dest.stem}-{number}.html"
    if not dest.exists():
        dest.write_text(content, encoding="utf-8")
    return dest.name


def reveal(workspace: Workspace, name: str) -> None:
    workspace.renders.mkdir(exist_ok=True)
    target = workspace.renders / Path(name).name if name else workspace.renders
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", str(target)] if name else ["open", str(workspace.renders)])
    elif sys.platform.startswith("win"):
        subprocess.run(["explorer", "/select,", str(target)] if name else ["explorer", str(workspace.renders)])
    else:
        subprocess.run(["xdg-open", str(workspace.renders)])


class Studio:
    """The Studio web server. Runs in the foreground (CLI) or a background thread (MCP)."""

    def __init__(self, workspace: Workspace, port: int = DEFAULT_PORT):
        self.workspace = workspace
        self.port = port
        self.jobs = Jobs()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    @property
    def running(self) -> bool:
        return self._server is not None

    def start(self) -> None:
        """Bind the port. Raises OSError if something (often another Studio) already uses it."""
        if self._server:
            return
        handler = make_handler(self.workspace, self.jobs, self.stop)
        self._server = ThreadingHTTPServer(("127.0.0.1", self.port), handler)

    def serve_in_background(self) -> None:
        self.start()
        if not self._thread or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()

    def serve_forever(self) -> None:
        self.start()
        try:
            self._server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        server, self._server = self._server, None
        if server:
            server.shutdown()
            server.server_close()

    def open_in_browser(self, prototype: str | None = None) -> str:
        url = self.url + (f"#{prototype}" if prototype else "")
        webbrowser.open(url)
        return url
