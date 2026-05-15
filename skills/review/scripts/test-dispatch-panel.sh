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

review_stub="$TMP/launch-review.sh"
cat > "$review_stub" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
out=""
tool=""
agent=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) out="$2"; shift 2 ;;
    --tool) tool="$2"; shift 2 ;;
    --agent-file) agent="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf '%s output from %s\n' "$tool" "$agent" > "$out"
printf '0\n' > "$out.done"
printf 'STATUS=clean\n' > "$out.dirty-tree"
printf 'OUTER_LAUNCHER=review\nTOOL=%s\nAGENT_FILE=%s\n' "$tool" "$agent" > "$out.meta"
STUB
chmod +x "$review_stub"

out=$("$SCRIPT" --mode diff --review-tmpdir "$TMP/both" --codex-available false --cursor-available false --launch-claude-subprocess "$stub")
assert_stdout_cap "$out"
sleep 0.2
grep -Fq 'PANEL_MODE=both-down' <<< "$out"
grep -Fq 'PANEL_SHAPE=hard' <<< "$out"
grep -Fq 'SLOT_COUNT=1' <<< "$out"
[[ -f "$TMP/both/claude-generic-output.txt.done" ]]

out=$("$SCRIPT" --mode diff --review-tmpdir "$TMP/simple" --codex-available true --cursor-available true --panel simple --launch-claude-subprocess "$stub" --launch-review "$review_stub")
assert_stdout_cap "$out"
sleep 0.2
grep -Fq 'DISPATCH_OK=true' <<< "$out"
grep -Fq 'PANEL_MODE=normal' <<< "$out"
grep -Fq 'PANEL_SHAPE=simple' <<< "$out"
grep -Fq 'SLOT_COUNT=3' <<< "$out"
[[ -f "$TMP/simple/cursor-specialist-edge-cases-output.txt.done" ]]
[[ -f "$TMP/simple/codex-specialist-structure-output.txt.done" ]]
[[ ! -e "$TMP/simple/cursor-specialist-plan-fidelity-output.txt.done" ]]

plan_file="$TMP/plan.md"
printf '# plan\n' > "$plan_file"
out=$("$SCRIPT" --mode diff --review-tmpdir "$TMP/simple-plan" --codex-available true --cursor-available true --panel simple --plan-file "$plan_file" --launch-claude-subprocess "$stub" --launch-review "$review_stub")
assert_stdout_cap "$out"
sleep 0.2
grep -Fq 'PANEL_SHAPE=simple' <<< "$out"
grep -Fq 'SLOT_COUNT=5' <<< "$out"
[[ -f "$TMP/simple-plan/cursor-specialist-plan-fidelity-output.txt.done" ]]
[[ -f "$TMP/simple-plan/codex-specialist-plan-fidelity-output.txt.done" ]]

out=$("$SCRIPT" --mode diff --review-tmpdir "$TMP/hard" --codex-available true --cursor-available true --panel hard --launch-claude-subprocess "$stub" --launch-review "$review_stub")
assert_stdout_cap "$out"
sleep 0.2
grep -Fq 'PANEL_SHAPE=hard' <<< "$out"
grep -Fq 'SLOT_COUNT=13' <<< "$out"
[[ -f "$TMP/hard/cursor-specialist-security-output.txt.done" ]]
[[ -f "$TMP/hard/codex-specialist-plan-fidelity-output.txt.done" ]]

echo "All assertions passed."
