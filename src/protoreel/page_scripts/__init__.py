"""JavaScript that Protoreel injects into the prototype page.

The scripts live next to this file as plain .js so they are easy to read and edit.
"""

from __future__ import annotations

from functools import cache
from importlib import resources


@cache
def load(name: str) -> str:
    """Return the text of one of the bundled scripts, e.g. load("clock.js")."""
    return resources.files(__package__).joinpath(name).read_text(encoding="utf-8")


def clock() -> str:
    """Init script that freezes time so the renderer can step it frame by frame."""
    return load("clock.js")


def cursor() -> str:
    """A function expression: (scale) => installs window.__cursor()."""
    return load("cursor.js")


def locate() -> str:
    """A function expression: (selector) => the element's box in the top page, iframes included."""
    return load("locate.js")


def scroll() -> str:
    """A function expression: ([x, y, dx, dy]) => scrolls whatever is under the point."""
    return load("scroll.js")


def background_function() -> str:
    """The recBackground(document, color) function declaration (shared with the Studio UI)."""
    return load("background.js")


def decorations() -> str:
    """A function expression: ([caption, background]) => adds the optional caption and backdrop."""
    return (
        "([caption, bg]) => {\n"
        "  if (bg) (" + background_function() + ")(document, bg);\n"
        "  if (caption) {\n"
        "    const d = document.createElement('div');\n"
        "    d.textContent = caption;\n"
        "    Object.assign(d.style, {position:'fixed', left:'0', right:'0', bottom:'6%', textAlign:'center',\n"
        "      zIndex:'2147483646', pointerEvents:'none', letterSpacing:'-.01em', color:'#8a8a86',\n"
        "      font:'500 15px -apple-system, BlinkMacSystemFont, Geist, system-ui, sans-serif'});\n"
        "    document.documentElement.appendChild(d);\n"
        "  }\n"
        "}"
    )
