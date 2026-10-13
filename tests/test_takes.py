from protoreel.takes import Take, prepare_events


def make_take():
    events = [{"type": "move", "t": 1000 + i * 16, "x": 100 + i, "y": 50} for i in range(10)]
    events.insert(3, {"type": "down", "t": 1040, "x": 103, "y": 50})
    events.append({"type": "up", "t": 1200, "x": 110, "y": 50})
    return Take(page="p.html", viewport_width=500, viewport_height=600, events=events)


def test_round_trip(tmp_path):
    path = make_take().save(tmp_path)
    again = Take.load(path)
    assert again.viewport_width == 500 and len(again.events) == 12


def test_studio_shape_is_accepted():
    take = Take.from_dict({"vw": 540, "vh": 675, "size": "4x5", "zoom": 2, "events": []}, page="x.html")
    assert (take.viewport_width, take.format, take.page) == (540, "4x5", "x.html")


def test_prepare_shifts_time_and_recentres():
    events, duration = prepare_events(make_take(), 700, 600, smooth=False, lead_in_ms=500, tail_ms=700)
    assert events[0]["t"] == 500
    assert events[0]["x"] == 200  # 100 + (700 - 500) / 2
    assert duration == events[-1]["t"] + 700
