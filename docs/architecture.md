# How Protoreel is built

Protoreel is about 1,800 lines of Python (half of it comments and docstrings) plus three small JavaScript files and the Studio page. Each module does one job.

```
src/protoreel/
├── cli.py            command line: studio, record, render-take, mcp, setup
├── mcp_server.py     the MCP server and its six tools
├── renderer.py       opens a page, plays an interaction, films it frame by frame
├── timeline.py       scripts and takes → one input state per frame
├── takes.py          takes captured in the Studio: load, save, smooth, re-centre
├── settings.py       formats, resolutions and defaults
├── workspace.py      the folder of prototypes, renders and takes; a tiny file server
├── encoder.py        ffmpeg: PNG frames in, MP4 out, plus the soundtrack
├── audio.py          asks the page for its sound (window.__recorderAudio)
├── browser.py        launches Chromium, installing it on first use
├── page_scripts/     JavaScript injected into the prototype
│   ├── clock.js        freezes time so we can step it
│   ├── cursor.js       the on-screen pointer (arrow or touch dot)
│   ├── locate.js       finds an element's box, looking inside iframes too
│   ├── scroll.js       scrolls whatever is under the pointer
│   └── background.js   optional backdrop colour
└── studio/
    ├── server.py       the Studio's web server and JSON API
    └── static/index.html  the Studio app (plain HTML/CSS/JS)
```

## The one idea that makes it work: a frozen clock

Normally a browser animates in real time, so a slow machine (or a slow screenshot) drops frames.
`page_scripts/clock.js` replaces `requestAnimationFrame`, `setTimeout`, `setInterval`,
`performance.now`, `Date.now` and every CSS/Web Animation with versions driven by a number we
control. The renderer then repeats, for every frame:

1. apply this frame's input (move the mouse, press, type, scroll) — `renderer.Player.step`
2. advance the page's clock by exactly 1/60 s — `window.__advance(ms)`
3. take a screenshot and pipe it to ffmpeg — `encoder.VideoEncoder`

So a 5-second video at 60 fps is exactly 300 screenshots, each showing precisely the right moment.

## From an interaction to frames

`timeline.py` turns both kinds of interaction into the same stream of `FrameInput` objects:

- **Takes** (`take_frames`) replay captured events at their recorded times.
- **Scripts** (`script_frames`) expand each action into frames. Element positions are looked up
  *when the action starts*, so earlier actions can open menus or move things around.

The renderer doesn't know or care which kind it is playing.

## Where things run

| You run | What happens |
| --- | --- |
| `protoreel studio` | `studio.server.Studio` serves the app at http://127.0.0.1:8765 |
| `protoreel mcp` | `mcp_server.build_server` serves tools over stdio; `open_studio` starts the Studio in a background thread |
| `protoreel record` | `renderer.render` directly |

Every render serves the prototype's folder from a throwaway local web server
(`workspace.PrototypeServer`), so pages load over `http://` and behave like they do in a real browser.

## Tests

`pytest` runs everything, including real renders, a real Studio and a real MCP session over
stdio (about 30 seconds). Unit tests for the timeline and takes need no browser.
