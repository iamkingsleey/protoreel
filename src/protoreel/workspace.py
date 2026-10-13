"""The workspace: the folder Protoreel works in.

    <workspace>/            your .html prototypes
    <workspace>/renders/    finished .mp4 videos
    <workspace>/takes/      takes captured in the Studio (.json)

The folder comes from `--folder`, else the PROTOREEL_HOME environment variable,
else ~/Protoreel.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

SKELETON = (
    '<!doctype html><html><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>{}</body></html>'
)

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".mp4": "video/mp4",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".glb": "model/gltf-binary",
    ".gltf": "model/gltf+json",
    ".wasm": "application/wasm",
}


def default_folder() -> Path:
    return Path(os.environ.get("PROTOREEL_HOME", "~/Protoreel")).expanduser()


@dataclass
class Workspace:
    folder: Path

    @classmethod
    def open(cls, folder: str | Path | None = None) -> Workspace:
        path = Path(folder).expanduser() if folder else default_folder()
        path.mkdir(parents=True, exist_ok=True)
        return cls(path.resolve())

    @property
    def renders(self) -> Path:
        return self.folder / "renders"

    @property
    def takes(self) -> Path:
        return self.folder / "takes"

    def prototypes(self) -> list[Path]:
        """Every .html file directly in the workspace, alphabetically."""
        return sorted(p for p in self.folder.glob("*.html") if p.is_file())

    def find_prototype(self, name: str) -> Path:
        """Accept a file name in the workspace, a path relative to it, or an absolute path."""
        candidate = Path(name).expanduser()
        for path in (candidate, self.folder / candidate, self.folder / f"{candidate}.html"):
            if path.is_file():
                return path.resolve()
        raise FileNotFoundError(
            f"Could not find '{name}'. Prototypes in {self.folder}: "
            + (", ".join(p.name for p in self.prototypes()) or "none yet")
        )

    def find_take(self, name: str) -> Path:
        candidate = Path(name).expanduser()
        for path in (candidate, self.takes / candidate, self.takes / f"{candidate}.json"):
            if path.is_file():
                return path.resolve()
        raise FileNotFoundError(f"Could not find the take '{name}' in {self.takes}.")

    def recent(self, folder: Path, pattern: str, limit: int = 20) -> list[Path]:
        if not folder.exists():
            return []
        return sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]


# ---------------------------------------------------------------- serving files
def safe_join(root: Path, relative: str) -> Path | None:
    """Join a URL path onto a folder without letting it climb out of that folder."""
    path = (root / unquote(relative)).resolve()
    return path if path == root or root in path.parents else None


def read_for_browser(path: Path) -> tuple[bytes, str]:
    """File bytes and content type. Bare HTML fragments get wrapped in a minimal document."""
    data = path.read_bytes()
    ctype = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
    if path.suffix.lower() in (".html", ".htm") and b"<html" not in data[:4000].lower():
        data = SKELETON.format(data.decode("utf-8", "replace")).encode()
    return data, ctype


class PrototypeServer:
    """Serves one folder on a random local port while a render runs.

    Pages load over http:// rather than file:// so fonts, fetch() and modules behave
    the same way they do in a real browser.
    """

    def __init__(self, root: Path):
        self.root = root.resolve()
        root_dir = self.root

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                path = safe_join(root_dir, urlparse(self.path).path.lstrip("/"))
                if not path or not path.is_file():
                    self.send_error(404)
                    return
                data, ctype = read_for_browser(path)
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def url_for(self, path: Path) -> str:
        relative = path.resolve().relative_to(self.root).as_posix()
        return f"http://127.0.0.1:{self._server.server_address[1]}/{relative}"

    def __enter__(self) -> PrototypeServer:
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._server.shutdown()
        self._server.server_close()
