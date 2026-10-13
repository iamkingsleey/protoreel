"""The Studio's HTTP API, end to end: save a take, render it, fetch the video."""

import json
import socket
import time
import urllib.request

from protoreel.studio.server import Studio


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def call(url: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read())


def test_capture_save_and_render(workspace):
    studio = Studio(workspace, free_port())
    studio.serve_in_background()
    try:
        page = urllib.request.urlopen(studio.url).read().decode()
        assert "Protoreel" in page and "recBackground" in page  # the shared JS was inlined
        files = call(studio.url + "api/files")
        assert files["protos"] == ["like-button.html"]

        take = {
            "vw": 540,
            "vh": 540,
            "size": "1x1",
            "zoom": 2,
            "events": [{"type": "move", "t": i * 16, "x": 300 + i * 2, "y": 400} for i in range(15)],
        }
        saved = call(studio.url + "api/takes", {"page": "like-button.html", "take": take})
        assert (workspace.takes / saved["name"]).exists()

        job = call(
            studio.url + "api/render",
            {
                "page": "like-button.html",
                "size": "1x1",
                "zoom": 2,
                "fps": 30,
                "res": "1080",
                "sound": False,
                "take": take,
            },
        )
        for _ in range(240):
            state = call(studio.url + f"api/job/{job['id']}")
            if state["state"] in ("done", "error"):
                break
            time.sleep(0.25)
        assert state["state"] == "done", state
        video = urllib.request.urlopen(studio.url + "renders/" + state["out"]).read()
        assert len(video) > 5_000
    finally:
        studio.stop()
