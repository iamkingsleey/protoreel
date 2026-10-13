"""End-to-end: these launch Chromium and ffmpeg, so they take a few seconds each."""

from protoreel.renderer import RenderOptions, output_path, render, still
from protoreel.takes import Take


async def test_script_render_makes_a_video_with_sound(workspace, quick_script):
    options = RenderOptions(format="1x1", zoom=2.0, fps=30)
    page = workspace.find_prototype("like-button")
    out = output_path(workspace.renders, page.name, options)
    result = await render(page, quick_script, options, out)
    assert out.exists() and out.stat().st_size > 10_000
    assert (result.width, result.height) == (1080, 1080)
    assert result.sound == "added"  # the example page exposes window.__recorderAudio


async def test_take_render(workspace):
    events = [{"type": "move", "t": i * 16, "x": 200 + i * 3, "y": 300} for i in range(20)]
    take = Take(page="like-button.html", viewport_width=540, viewport_height=540, format="1x1", events=events)
    options = RenderOptions(format="1x1", fps=30, sound=False)
    out = output_path(workspace.renders, "like-button.html", options, "take-test")
    result = await render(workspace.find_prototype("like-button.html"), take, options, out)
    assert result.path.name == "take-test.mp4" and result.frames > 20


async def test_still_is_a_png(workspace):
    png = await still(workspace.find_prototype("like-button.html"), RenderOptions(format="1x1"))
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
