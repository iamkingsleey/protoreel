"""End-to-end: these launch Chromium and ffmpeg, so they take a few seconds each."""

from protoreel.renderer import Player, RenderOptions, element_resolver, open_page, output_path, render, still
from protoreel.takes import Take
from protoreel.timeline import FrameInput


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


PHONE_FRAME = """<!doctype html><body style="margin:0">
<iframe id="app" style="position:absolute;left:100px;top:50px;width:200px;height:300px;border:0;
  transform:scale(.5);transform-origin:0 0" srcdoc="<button id='go' style='margin:40px'>Go</button>
  <script>go.onclick = () => setTimeout(() => go.textContent = 'Done', 200)</script>"></iframe></body>"""


async def test_prototypes_inside_an_iframe_can_be_clicked_and_keep_time(tmp_path):
    """An app shown inside a device frame: selectors reach into the iframe and its clock runs."""
    page_file = tmp_path / "phone.html"
    page_file.write_text(PHONE_FRAME)
    options = RenderOptions(format="1x1", fps=30, sound=False)
    async with open_page(page_file, options) as page:
        geometry = options.geometry()
        x, y = await element_resolver(page, geometry.viewport_width, geometry.viewport_height)("#go")
        assert 100 < x < 200 and 50 < y < 200  # inside the scaled frame, not at the button's own coordinates
        player = Player(page, options)
        await player.step(FrameInput(x, y, True))
        await player.step(FrameInput(x, y, False))
        for _ in range(10):  # 330 ms of page time
            await player.step(FrameInput(x, y, False))
        assert await page.frames[1].evaluate("document.getElementById('go').textContent") == "Done"
