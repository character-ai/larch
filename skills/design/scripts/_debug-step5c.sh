#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
TMP=$(mktemp -d)
D="$TMP/d"
mkdir -p "$D/.completed"
: >"$D/.completed/step-5b"
FAKE="$TMP/p"
mkdir -p "$FAKE/skills/design/scripts" "$FAKE/skills/implement/scripts" "$FAKE/scripts"
ln -sf "$ROOT/skills/design/scripts/design-stage-terminal-state.sh" "$FAKE/skills/design/scripts/"
ln -sf "$ROOT/skills/implement/scripts/stall-recovery-report.sh" "$FAKE/skills/implement/scripts/"
ln -sf "$ROOT/scripts/lib-design-tmpdir.sh" "$FAKE/scripts/"
ln -sf "$ROOT/scripts/lib-quiet.sh" "$FAKE/scripts/"
mkdir -p "$FAKE/python"
printf '#!/usr/bin/env python3\nimport sys\nif len(sys.argv)>=3 and sys.argv[1]=="design" and sys.argv[2]=="publish": raise SystemExit(2)\nif len(sys.argv)>=3 and sys.argv[1]=="design" and sys.argv[2]=="render-final-summary":\n  import os; open(os.path.join(os.environ.get("DESIGN_TMPDIR",""), "final-summary.md"), "w").close(); raise SystemExit(0)\nraise SystemExit(2)\n' >"$FAKE/python/cli.py"
chmod +x "$FAKE/python/cli.py"
set +e
CLAUDE_PLUGIN_ROOT="$FAKE" DESIGN_TMPDIR="$D" "$ROOT/skills/design/scripts/design-step5c.sh" 2>"$D/err"
rc=$?
set -e
printf 'rc=%s\n' "$rc"
ls -la "$D"
cat "$D/err" || true
cat "$D/design-stage-terminal-state.stderr.log" 2>/dev/null || true
cat "$D/design-stage-terminal-state.stdout.log" 2>/dev/null || true
