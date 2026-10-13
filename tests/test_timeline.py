import pytest

from protoreel.timeline import ScriptError, ease, script_frames


async def fixed_resolver(point):
    """Resolve '#a' to (100, 100) and plain [x, y] lists to themselves."""
    if point == "#a":
        return 100.0, 100.0
    return tuple(float(str(v).rstrip("%")) for v in point)


async def collect(script, fps=60):
    return [f async for f in script_frames(script, fixed_resolver, fps, lead_in_ms=0, tail_ms=0)]


def test_ease_starts_at_zero_and_ends_at_one():
    for name in ("smooth", "linear", "in", "out", "inout"):
        assert ease(name, 0) == pytest.approx(0)
        assert ease(name, 1) == pytest.approx(1)


async def test_wait_holds_still_for_the_right_number_of_frames():
    frames = await collect({"start": [10, 10], "actions": [{"wait": 500}]})
    assert len(frames) == 30
    assert {(f.x, f.y) for f in frames} == {(10, 10)}


async def test_click_glides_then_presses_and_releases():
    frames = await collect({"start": [0, 0], "actions": [{"click": "#a", "dur": 100}]})
    assert (frames[-1].x, frames[-1].y) == (100, 100)
    pressed = [f.down for f in frames]
    assert True in pressed and pressed[-1] is False


async def test_drag_by_offset_ends_released_at_the_target():
    frames = await collect({"start": [10, 10], "actions": [{"drag": {"by": [50, 0]}, "dur": 200}]})
    assert frames[0].down and not frames[-1].down
    assert frames[-1].x == pytest.approx(60)


async def test_typing_sends_one_character_at_a_time():
    frames = await collect({"start": [0, 0], "actions": [{"type": "hey", "delay": 50}]})
    assert "".join(f.text for f in frames) == "hey"


async def test_scroll_adds_up_to_the_requested_distance():
    frames = await collect({"start": [0, 0], "actions": [{"scroll": {"by": [0, 300]}, "dur": 400}]})
    assert sum(f.scroll[1] for f in frames) == pytest.approx(300)


async def test_unknown_action_is_reported_clearly():
    with pytest.raises(ScriptError, match="unknown step 'jump'"):
        await collect({"actions": [{"jump": 1}]})


async def test_swipe_moves_the_pointer_against_the_scroll_and_looks_pressed():
    frames = await collect({"start": [50, 80], "actions": [{"scroll": {"by": [0, 300]}, "dur": 500, "swipe": True}]})
    assert sum(f.scroll[1] for f in frames) == pytest.approx(300)
    assert frames[-1].y < 80  # the finger travelled up while the page scrolled down
    assert any(f.touch for f in frames) and not any(f.down for f in frames)
