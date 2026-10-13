# Changelog

## 0.1.1 — 2026-10-13

Better mobile prototypes.

- Apps shown inside a phone frame (`<iframe>`) now animate correctly: the frame-by-frame clock reaches into iframes
- Script selectors find elements inside same-origin iframes, including scaled ones
- `--pointer touch` (and `pointer: "touch"` in the MCP tools) draws a fingertip dot instead of an arrow
- `"swipe": true` on a scroll moves the pointer like a finger dragging the page
- Scrolling now moves whatever is under the pointer (a scrollable panel or an iframe), not only the top page

## 0.1.0 — 2026-10-13

First open-source release, grown out of a personal "Recorder Studio" script.

- MCP server with `list_workspace`, `record_video`, `render_take`, `preview_frame`, `open_studio` and `check_setup`
- Studio web app for hand-captured takes; takes are now saved to `takes/` so they can be re-rendered later
- Scripts gain `click`, `hover`, `type` and `scroll` actions, CSS-selector points, and late element lookup
- Bundled ffmpeg fallback and automatic Chromium install
- Six social formats from 1080 to 4K, optional backdrop and caption, prototype sound
