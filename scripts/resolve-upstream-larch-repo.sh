#!/usr/bin/env bash
# resolve-upstream-larch-repo.sh — resolve the plugin's canonical upstream GitHub repo.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"

python3 - "$PLUGIN_ROOT/.claude-plugin/plugin.json" <<'PY'
import json
import re
import sys
from urllib.parse import urlparse

path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    print("resolve-upstream-larch-repo: could not read plugin metadata", file=sys.stderr)
    sys.exit(1)

repo = data.get("repository")
if not isinstance(repo, str) or not repo.strip():
    print("resolve-upstream-larch-repo: repository metadata missing", file=sys.stderr)
    sys.exit(1)
if any(ch in repo for ch in "\r\n\t"):
    print("resolve-upstream-larch-repo: repository metadata must be single-value", file=sys.stderr)
    sys.exit(1)
repo = repo.strip()
if ".." in repo or repo.startswith("/"):
    print("resolve-upstream-larch-repo: repository metadata is malformed", file=sys.stderr)
    sys.exit(1)

owner_repo = None
if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?", repo):
    owner_repo = repo
else:
    candidate = repo
    if candidate.startswith("git+"):
        candidate = candidate[4:]
    if candidate.startswith("git@github.com:"):
        owner_repo = candidate[len("git@github.com:"):]
    else:
        parsed = urlparse(candidate)
        host = parsed.netloc.rsplit("@", 1)[-1].lower()
        if parsed.scheme not in {"https", "ssh", "git"} or host != "github.com":
            print("resolve-upstream-larch-repo: repository must be a GitHub URL or OWNER/REPO", file=sys.stderr)
            sys.exit(1)
        owner_repo = parsed.path.lstrip("/")

if owner_repo.endswith(".git"):
    owner_repo = owner_repo[:-4]
if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", owner_repo or ""):
    print("resolve-upstream-larch-repo: repository owner/name is malformed", file=sys.stderr)
    sys.exit(1)
owner, name = owner_repo.split("/", 1)
if owner in {".", ".."} or name in {".", ".."}:
    print("resolve-upstream-larch-repo: repository owner/name is malformed", file=sys.stderr)
    sys.exit(1)
print(f"{owner}/{name}")
PY
