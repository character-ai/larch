#!/usr/bin/env bash
# test-run-analysis-quiet.sh - Verify run-analysis.sh restores quiet streams.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-report-tokens-test.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

mkdir -p "$TMPROOT/larch-logs/implement/run1"
cat > "$TMPROOT/larch-logs/implement/run1/manifest.json" <<'JSON'
{"issue_number":1,"started_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:01:00Z"}
JSON
cat > "$TMPROOT/larch-logs/implement/run1/token-report.json" <<'JSON'
{"claude":{"totals":{"total":1000}},"BUCKETS_claude":{"input":1000,"output":0}}
JSON
mkdir -p "$TMPROOT/larch-logs/design/run1"
cat > "$TMPROOT/larch-logs/design/run1/manifest.json" <<'JSON'
{"issue_number":2,"started_at":"2026-01-02T00:00:00Z","updated_at":"2026-01-02T00:01:00Z"}
JSON
cat > "$TMPROOT/larch-logs/design/run1/token-report-final.json" <<'JSON'
{"claude":{"totals":{"total":2000}},"BUCKETS_claude":{"input":2000,"output":0}}
JSON
cat > "$TMPROOT/larch-logs/design/run1/run-params.json" <<'JSON'
{"design_classification":"HARD"}
JSON
cat > "$TMPROOT/git" <<'SHIM'
#!/usr/bin/env bash
if [ "$1 $2" = "rev-parse --show-toplevel" ]; then
  printf '%s\n' "$LARCH_TEST_ROOT"
  exit 0
fi
exec /usr/bin/git "$@"
SHIM
chmod +x "$TMPROOT/git"
PYTHON_BIN="$(command -v python3)"
cat > "$TMPROOT/python3" <<SHIM
#!/usr/bin/env bash
if [ "\$1" = "-c" ] && printf '%s\n' "\$2" | grep -Fq 'sys.version_info >= (3, 12)'; then
  exit 0
fi
exec "$PYTHON_BIN" "\$@"
SHIM
chmod +x "$TMPROOT/python3"

stdout_file="$TMPROOT/stdout.txt"
stderr_file="$TMPROOT/stderr.txt"
PATH="$TMPROOT:$PATH" \
LARCH_TEST_ROOT="$TMPROOT" \
LARCH_QUIET_ACTIVE=1 \
LARCH_QUIET_PID=999999 \
LARCH_REPORT_TOKENS_NO_ISSUE=1 \
LARCH_REPORT_TOKENS_NO_PLOT=1 \
CLAUDE_PLUGIN_ROOT="$ROOT" \
  "$ROOT/skills/report-tokens/scripts/run-analysis.sh" --skill implement --no-issue --no-plot >"$stdout_file" 2>"$stderr_file"

grep -Fq '## Report Tokens Analysis' "$stdout_file"
grep -Fq 'Cache JSON:' "$stdout_file"
grep -Fq 'Scanning ' "$stderr_file"

stdout_file="$TMPROOT/design-stdout.txt"
stderr_file="$TMPROOT/design-stderr.txt"
PATH="$TMPROOT:$PATH" \
LARCH_TEST_ROOT="$TMPROOT" \
LARCH_QUIET_ACTIVE=1 \
LARCH_QUIET_PID=999999 \
LARCH_REPORT_TOKENS_NO_ISSUE=1 \
LARCH_REPORT_TOKENS_NO_PLOT=1 \
CLAUDE_PLUGIN_ROOT="$ROOT" \
  "$ROOT/skills/report-tokens/scripts/run-analysis.sh" --skill design --no-issue --no-plot >"$stdout_file" 2>"$stderr_file"
grep -Fq '## Report Tokens Analysis' "$stdout_file"
grep -Fq '### HARD' "$stdout_file"
grep -Fq 'Cache JSON:' "$stdout_file"
grep -Fq 'Scanning ' "$stderr_file"

stdout_file="$TMPROOT/plot-from-stdout.txt"
stderr_file="$TMPROOT/plot-from-stderr.txt"
set +e
PATH="$TMPROOT:$PATH" \
LARCH_TEST_ROOT="$TMPROOT" \
LARCH_QUIET_ACTIVE=1 \
LARCH_QUIET_PID=999999 \
CLAUDE_PLUGIN_ROOT="$ROOT" \
  "$ROOT/skills/report-tokens/scripts/run-analysis.sh" --skill implement --plot-from 1 >"$stdout_file" 2>"$stderr_file"
status=$?
set -e
[ "$status" -eq 2 ]
grep -Fq -- '--plot-from has been removed' "$stderr_file"

stdout_file="$TMPROOT/invalid-skill-stdout.txt"
stderr_file="$TMPROOT/invalid-skill-stderr.txt"
set +e
PATH="$TMPROOT:$PATH" \
LARCH_TEST_ROOT="$TMPROOT" \
LARCH_QUIET_ACTIVE=1 \
LARCH_QUIET_PID=999999 \
CLAUDE_PLUGIN_ROOT="$ROOT" \
  "$ROOT/skills/report-tokens/scripts/run-analysis.sh" --skill bogus >"$stdout_file" 2>"$stderr_file"
status=$?
set -e
[ "$status" -eq 1 ]
grep -Fq -- '--skill must be design or implement' "$stderr_file"

stdout_file="$TMPROOT/repo-fail-stdout.txt"
stderr_file="$TMPROOT/repo-fail-stderr.txt"
set +e
PATH="$TMPROOT:$PATH" \
LARCH_TEST_ROOT="$TMPROOT" \
LARCH_QUIET_ACTIVE=1 \
LARCH_QUIET_PID=999999 \
LARCH_REPORT_TOKENS_REPO="../bad/repo" \
LARCH_REPORT_TOKENS_NO_PLOT=1 \
CLAUDE_PLUGIN_ROOT="$ROOT" \
  "$ROOT/skills/report-tokens/scripts/run-analysis.sh" --skill implement --no-plot >"$stdout_file" 2>"$stderr_file"
status=$?
set -e
[ "$status" -eq 4 ]
grep -Fq 'LARCH_REPORT_TOKENS_REPO must be a safe OWNER/REPO slug' "$stderr_file"
