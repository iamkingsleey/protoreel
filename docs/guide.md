# Protoreel guide

Everything you need to set up and use Protoreel. For a quick overview, see the [README](../README.md).


## Quick start

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) (one line to install). Then:

```bash
uvx protoreel setup --folder ~/Prototypes
```

That downloads Chromium (once), creates the folder, and prints the config for your AI client. Put your `.html` prototypes in that folder.

### Use it from Claude, Cursor or VS Code (MCP)

**Claude Desktop / Cowork** — open *Settings → Developer → Edit Config* and add:

```json
{
  "mcpServers": {
    "protoreel": {
      "command": "uvx",
      "args": ["protoreel", "mcp", "--folder", "/Users/you/Prototypes"]
    }
  }
}
```

If Claude says it can't start the server, replace `"uvx"` with the full path that `which uvx` prints (desktop apps don't always see your shell's PATH). `protoreel setup` prints the snippet with the full path filled in.

**Claude Code**

```bash
claude mcp add protoreel -- uvx protoreel mcp --folder ~/Prototypes
```

**Cursor** (`.cursor/mcp.json`) uses the same block as Claude Desktop. **VS Code** (`.vscode/mcp.json`) uses the key `"servers"` instead of `"mcpServers"`.

Restart the app, then just ask:

> *"Record checkout.html as a 9:16 video: tap the Add to bag button, wait a second, then open the bag."*

> *"Open the Protoreel studio for like-button.html so I can record it myself."*

> *"Re-render my last take as a 4:5 and a 16:9."*

### Use the Studio yourself

```bash
uvx protoreel studio --folder ~/Prototypes
```

Pick a prototype, choose a format, press **Capture**, perform the interaction with your mouse, press **Esc**, then **Render**. Every take is saved to `takes/`, so you (or your AI assistant) can render it again later in another format.

### Use the command line

```bash
uvx protoreel record like-button.html examples/like-button.json --format 9x16 --zoom 2.4
uvx protoreel render-take like-button_20261013-101500.json --format 16x9 --res 4k
```

---

## The MCP tools

| Tool | What it does |
| --- | --- |
| `list_workspace` | Lists prototypes, recent takes and recent videos |
| `record_video` | Films a prototype following a script (below) |
| `render_take` | Films a take captured in the Studio, in any format |
| `preview_frame` | Returns one frame as an image, to check framing and zoom |
| `open_studio` | Opens the Studio in your browser |
| `check_setup` | Checks Chromium and ffmpeg (and can install Chromium) |

## Scripts

A script is a list of actions, played in order. Elements are found with CSS selectors *at the moment each action starts*, so menus that open mid-video work naturally.

```json
{
  "start": ["80%", "85%"],
  "actions": [
    {"wait": 400},
    {"click": "#add-to-bag", "dur": 800},
    {"wait": 900},
    {"type": "Lekki Phase 1", "delay": 60},
    {"key": "Enter"},
    {"drag": {"by": [0, -220]}, "dur": 900},
    {"scroll": {"to": "#reviews"}, "dur": 1000},
    {"wait": 1200}
  ]
}
```

| Action | Meaning |
| --- | --- |
| `{"wait": 500}` | hold still for 500 ms |
| `{"move": POINT, "dur": 600}` / `{"hover": POINT}` | glide the pointer to a point |
| `{"click": POINT, "dur": 500}` | glide there, then press and release (`{"click": true}` clicks in place) |
| `{"drag": {"to": POINT} or {"by": [dx, dy]}, "dur": 900}` | press, move, release |
| `{"down": true}` / `{"up": true}` | press or release in place |
| `{"key": "Enter"}` | press a key ([names](https://playwright.dev/docs/api/class-keyboard#keyboard-press)) |
| `{"type": "Hello", "delay": 70}` | type text, one character every 70 ms |
| `{"scroll": {"by": [0, 400]} or {"to": POINT}, "dur": 800}` | scroll smoothly |

A **POINT** is `[x, y]` in CSS pixels, `["50%", "60%"]` of the frame, `"#selector"`, or `{"el": "#selector", "x": 0.5, "y": 0.5}` for a spot inside an element. Any action can take `"ease"`: `smooth` (default, like a hand), `linear`, `in`, `out` or `inout`.

## Formats and zoom

| Format | Size at 1080 | Typical use |
| --- | --- | --- |
| `4x5` | 1080 × 1350 | Instagram / LinkedIn feed |
| `9x16` | 1080 × 1920 | Reels, TikTok, Shorts |
| `1x1` | 1080 × 1080 | Square |
| `16x9` | 1920 × 1080 | Landscape, YouTube, X |
| `4x3` | 1600 × 1200 | Dribbble |
| `3x2` | 1800 × 1200 | Dribbble wide |

**Zoom** (0.6–3.6, default 2) is how large the prototype appears: the page is laid out at *format ÷ zoom* CSS pixels and rendered sharply at that scale. **Resolution** (`1080`, `2k`, `3k`, `4k`) adds pixels without changing the framing.

## Sound

Headless browsers can't record their own audio, so prototypes that make sound opt in with one function:

```js
// Return a base64 WAV of the sounds that played between startMs and startMs + durationMs
// (on the page's clock, i.e. performance.now()). A Promise of the string is fine too.
window.__recorderAudio = function (startMs, durationMs) { /* ... */ };
```

The usual pattern is to log each sound as it plays and replay the log into an `OfflineAudioContext`. [`examples/like-button.html`](../examples/like-button.html) shows the whole thing in about 15 lines. Pages without the function produce silent videos.

## Folder layout

```
~/Prototypes/          your .html prototypes (full pages or bare fragments)
~/Prototypes/renders/  finished videos
~/Prototypes/takes/    takes captured in the Studio
```

Set the folder with `--folder`, or the `PROTOREEL_HOME` environment variable (default `~/Protoreel`).

## Troubleshooting

- **"Chromium is not installed"** — run `uvx protoreel setup`. Behind a strict network? Point `PROTOREEL_CHROMIUM` at an existing Chrome/Chromium.
- **The Studio port is busy** — another Studio is probably running; `protoreel studio --port 8800` picks another.
- **The video is silent** — the page doesn't define `window.__recorderAudio`; see *Sound*.
- **Clicks miss** — use a selector rather than coordinates, and check with `preview_frame`.

## Contributing

Protoreel is small on purpose and written to be easy to read. Start with [docs/architecture.md](architecture.md), then see [CONTRIBUTING.md](../CONTRIBUTING.md).

## License

MIT © Kingsley Mkpandiok
