import pytest

from protoreel.settings import FORMATS, frame_geometry


def test_every_format_has_even_dimensions():
    for fmt in FORMATS:
        for res in ("1080", "2k", "3k", "4k"):
            g = frame_geometry(fmt, 2.0, res)
            assert g.video_width % 2 == 0 and g.video_height % 2 == 0


def test_zoom_shrinks_the_viewport_but_not_the_video():
    near, far = frame_geometry("4x5", 2.0, "1080"), frame_geometry("4x5", 1.0, "1080")
    assert near.viewport_width == 540 and far.viewport_width == 1080
    assert near.video_width == far.video_width == 1080


def test_resolution_keeps_the_framing():
    hd, uhd = frame_geometry("16x9", 2.0, "1080"), frame_geometry("16x9", 2.0, "4k")
    assert hd.viewport_width == uhd.viewport_width
    assert uhd.video_width == 2 * hd.video_width


@pytest.mark.parametrize("args", [("5x7", 2.0, "1080"), ("4x5", 9.0, "1080"), ("4x5", 2.0, "8k")])
def test_bad_values_are_explained(args):
    with pytest.raises(ValueError):
        frame_geometry(*args)
