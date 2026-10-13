# Protoreel — notes for Claude Code

Protoreel films HTML prototypes into social videos. It is a Python package with a CLI, an MCP
server and a small web Studio. Read `docs/architecture.md` for the map of modules.

## Strict rule: authorship

Never add Claude, Claude Code or Cowork as an author or co-author of anything in this project.
No `Co-Authored-By` trailers, no "Generated with Claude Code" lines in commits, pull requests,
releases or files. Commits are authored by the repository owner only.

## Commands

```bash
uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"   # set up
python -m playwright install chromium                               # once per machine
pytest -q                                                            # ~30 s, real renders
ruff check src tests && ruff format src tests                        # lint + format
protoreel studio --folder ~/Playwright                               # run the Studio
protoreel record examples/like-button.html examples/like-button.json # scripted render
```

## Conventions

- Keep it readable for a junior developer: one job per module, plain names, short docstrings,
  comments that explain *why*.
- Never print to stdout from code the MCP server runs: stdout carries the MCP protocol.
  Progress goes to stderr (CLI) or `ctx.report_progress` (MCP).
- Errors a user can fix raise `ValueError` / `FileNotFoundError` with a helpful message;
  `mcp_server.user_errors` passes those messages through to the AI client.
- The MCP SDK is v2 (`mcp.server.mcpserver.MCPServer`), not v1's `FastMCP`.
- Version lives in `src/protoreel/__init__.py`; update `CHANGELOG.md` with it.
