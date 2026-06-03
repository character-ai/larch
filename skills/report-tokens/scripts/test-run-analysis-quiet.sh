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
cat > "$TMPROOT/git" <<'SHIM'
#!/usr/bin/env bash
if [ "$1 $2" = "rev-parse --show-toplevel" ]; then
  printf '%s\n' "$LARCH_TEST_ROOT"
  exit 0
fi
exec /usr/bin/git "$@"
SHIM
chmod +x "$TMPROOT/git"

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
grep -Fq 'Scanning ' "$stderr_file"
