# Changelog

## 0.1.0 — 2026-10-13

First open-source release, grown out of a personal "Recorder Studio" script.

- MCP server with `list_workspace`, `record_video`, `render_take`, `preview_frame`, `open_studio` and `check_setup`
- Studio web app for hand-captured takes; takes are now saved to `takes/` so they can be re-rendered later
- Scripts gain `click`, `hover`, `type` and `scroll` actions, CSS-selector points, and late element lookup
- Bundled ffmpeg fallback and automatic Chromium install
- Six social formats from 1080 to 4K, optional backdrop and caption, prototype sound
