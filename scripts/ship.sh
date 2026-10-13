#!/usr/bin/env bash
# Publish Protoreel to GitHub and install it as an MCP server on this Mac.
#
#   scripts/ship.sh ~/Playwright          # workspace folder for your prototypes
#
# Safe to re-run: every step checks whether it has already been done.
set -euo pipefail

WORKSPACE="${1:-$HOME/Protoreel}"
REPO_NAME="protoreel"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

say()  { printf "\n\033[1m%s\033[0m\n" "$*"; }
fail() { printf "\n\033[31m%s\033[0m\n" "$*"; exit 1; }

# 1. tools -------------------------------------------------------------------
say "1/6  Checking tools"
command -v git >/dev/null || fail "git is missing. Install Xcode command line tools: xcode-select --install"
command -v uv  >/dev/null || { echo "Installing uv…"; curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }
command -v gh  >/dev/null || fail "GitHub CLI is missing. Install it with: brew install gh"
gh auth status >/dev/null 2>&1 || fail "Log in to GitHub first: gh auth login"
GH_USER="$(gh api user --jq .login)"
echo "GitHub user: $GH_USER"

# 2. fill in the GitHub username ----------------------------------------------
say "2/6  Pointing links at github.com/$GH_USER/$REPO_NAME"
grep -rl "YOUR_GITHUB_USERNAME" --include="*.py" --include="*.md" --include="*.toml" . 2>/dev/null \
  | grep -v "^./.venv" | grep -v "^./CLAUDE.md" | while read -r file; do
    sed -i '' "s/YOUR_GITHUB_USERNAME/$GH_USER/g" "$file"
    echo "  updated $file"
  done

# 3. lint and test ------------------------------------------------------------
say "3/6  Linting and testing (about a minute)"
[ -d .venv ] || uv venv -q
uv pip install -q -e ".[dev]"
uv run python -m playwright install chromium >/dev/null
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest -q

# 4. GitHub --------------------------------------------------------------------
say "4/6  GitHub repository"
[ -d .git ] || git init -q -b main
git add -A
git diff --cached --quiet || git commit -q -m "Point project links at $GH_USER"
if gh repo view "$GH_USER/$REPO_NAME" >/dev/null 2>&1; then
  echo "Repository exists, pushing."
  git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$GH_USER/$REPO_NAME.git"
  git push -u origin main
else
  gh repo create "$REPO_NAME" --public --source . --push \
    --description "Turn HTML prototypes into frame-perfect social videos, from a Studio app or any MCP client."
fi
gh repo edit "$GH_USER/$REPO_NAME" --add-topic mcp --add-topic mcp-server --add-topic playwright \
  --add-topic prototyping --add-topic video >/dev/null || true

# 5. install on this Mac and register with Claude ------------------------------
say "5/6  Installing Protoreel and registering the MCP server"
uv tool install --force --from "$ROOT" protoreel >/dev/null
PROTOREEL="$(command -v protoreel || echo "$HOME/.local/bin/protoreel")"
mkdir -p "$WORKSPACE"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"
"$PROTOREEL" setup --folder "$WORKSPACE" >/dev/null

CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
mkdir -p "$(dirname "$CONFIG")"
python3 - "$CONFIG" "$PROTOREEL" "$WORKSPACE" <<'PY'
import json, pathlib, sys
config, command, folder = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
data = json.loads(config.read_text()) if config.exists() and config.read_text().strip() else {}
if config.exists():
    config.with_suffix(".json.bak").write_text(config.read_text())
data.setdefault("mcpServers", {})["protoreel"] = {"command": command, "args": ["mcp", "--folder", folder]}
config.write_text(json.dumps(data, indent=2))
print(f"Claude Desktop: added 'protoreel' to {config} (backup saved next to it)")
PY
if command -v claude >/dev/null; then
  claude mcp remove protoreel -s user >/dev/null 2>&1 || true
  claude mcp add protoreel -s user -- "$PROTOREEL" mcp --folder "$WORKSPACE" && echo "Claude Code: added 'protoreel'"
fi

# 6. retire the old launcher ---------------------------------------------------
say "6/6  Tidying the old Recorder files"
mkdir -p "$WORKSPACE/_legacy"
for old in studio.py record.py Recorder.command; do
  [ -e "$WORKSPACE/$old" ] && mv -n "$WORKSPACE/$old" "$WORKSPACE/_legacy/" && echo "  moved $old to _legacy/"
done

say "Done. Restart Claude Desktop, then ask: \"Open the Protoreel studio\"."
cat <<EOF

Last step, publishing to PyPI (one time, about 2 minutes):
  1. Sign in at https://pypi.org (create an account if needed, with 2FA).
  2. Open https://pypi.org/manage/account/publishing/ and add a pending publisher:
       PyPI project name: protoreel
       Owner:             $GH_USER
       Repository name:   $REPO_NAME
       Workflow name:     release.yml
       Environment name:  pypi
  3. Then run:   git tag v0.1.0 && git push --tags
     The Release workflow publishes it. Anyone can then run:  uvx protoreel studio
EOF
