#!/usr/bin/env bash
# Regression harness for dispatch-panel.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review/scripts/dispatch-panel.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-dispatch-panel.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
export LARCH_EXECUTION_ISSUES_LOG="$TMP/execution-issues.md"

assert_stdout_cap() {
    local text="$1" cap="${2:-2048}" bytes
    bytes=${#text}
    [[ "$bytes" -le "$cap" ]] || { echo "FAIL: stdout ${bytes}B > ${cap}B cap" >&2; exit 1; }
}

stub="$TMP/launch-claude.sh"
cat > "$stub" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [[ $# -gt 0 ]]; do
  case "$1" in --output-file) out="$2"; shift 2 ;; *) shift ;; esac
done
printf 'claude output\n' > "$out"
printf '0\n' > "$out.done"
printf 'STATUS=clean\n' > "$out.dirty-tree"
printf 'OUTER_LAUNCHER=claude\nTOOL=claude\n' > "$out.meta"
STUB
chmod +x "$stub"

out=$("$SCRIPT" --mode diff --review-tmpdir "$TMP/both" --codex-available false --cursor-available false --launch-claude-subprocess "$stub")
assert_stdout_cap "$out"
sleep 0.2
grep -Fq 'PANEL_MODE=both-down' <<< "$out"
grep -Fq 'SLOT_COUNT=1' <<< "$out"
[[ -f "$TMP/both/claude-generic-output.txt.done" ]]

out=$("$SCRIPT" --mode diff --review-tmpdir "$TMP/cursor-down" --codex-available false --cursor-available false --launch-claude-subprocess "$stub")
assert_stdout_cap "$out"
sleep 0.2
grep -Fq 'DISPATCH_OK=true' <<< "$out"

echo "All assertions passed."
