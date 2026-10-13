# Handing Protoreel to Claude Code

Open Terminal and run:

```bash
cd ~/Playwright/protoreel
claude
```

Then paste this prompt:

> Read CLAUDE.md and docs/architecture.md, and follow its authorship rule strictly: never add
> yourself as a co-author or add "Generated with Claude" lines anywhere. Then ship Protoreel for me by running
> `scripts/ship.sh ~/Playwright`. If a step fails, fix the cause and re-run the script
> (it is safe to re-run). If GitHub login is needed, ask me to run `gh auth login`.
> When it finishes, walk me through the PyPI "pending publisher" step it prints, then push
> the v0.1.0 tag and watch the Release workflow until it succeeds. Finally, confirm the
> MCP server works by listing the protoreel tools.

That's it. After this, you never need `Recorder.command` again: ask Claude to
"open the Protoreel studio", or to record a prototype for you.
