#!/usr/bin/env bash
# Regression harness for scripts/dispatch-code-voters.sh waterfall wiring.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/dispatch-code-voters.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-dispatch-code-voters.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
unset CLAUDE_PLUGIN_ROOT

STUB_BIN="$TMP/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/codex" <<'STUB'
#!/usr/bin/env bash
out=""; last=""
log="${CODEX_STUB_LOG:-}"
for arg in "$@"; do [[ "$last" == "--output-last-message" ]] && out="$arg"; last="$arg"; done
[[ -n "$out" ]] || exit 9
[[ -n "$log" ]] && printf '%s\n' "$*" >> "$log"
printf 'FINDING_1: YES\n' > "$out"
STUB
cat > "$STUB_BIN/cursor" <<'STUB'
#!/usr/bin/env bash
log="${CURSOR_STUB_LOG:-}"
[[ -n "$log" ]] && printf '%s\n' "$*" >> "$log"
printf '{"result":"FINDING_1: NO -- cursor","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
STUB
cat > "$STUB_BIN/claude" <<'STUB'
#!/usr/bin/env bash
cat >/dev/null
case "${CLAUDE_STUB_MODE:-ok}" in
  empty) exit 0 ;;
  fail)
    printf 'stub claude failure\n' >&2
    exit 7 ;;
esac
printf 'FINDING_1: YES\n'
STUB
chmod +x "$STUB_BIN/codex" "$STUB_BIN/cursor" "$STUB_BIN/claude"

BALLOT="$TMP/ballot.md"
cat > "$BALLOT" <<'EOF'
### FINDING_1: First
- **Reviewer**: stub
- **Concern**: c1
- **Suggested revision**: r1
EOF

DIFF_FILE="$TMP/diff.txt"
PLAN_FILE="$TMP/plan.txt"
printf 'diff\n' > "$DIFF_FILE"
printf 'plan\n' > "$PLAN_FILE"
CODEX_LOG="$TMP/codex.log"
CURSOR_LOG="$TMP/cursor.log"

out=$(PATH="$STUB_BIN:$PATH" CODEX_STUB_LOG="$CODEX_LOG" CURSOR_STUB_LOG="$CURSOR_LOG" "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$TMP/happy" --codex-available true --cursor-available true --diff-file "$DIFF_FILE" --plan-file "$PLAN_FILE")
grep -Fq 'VOTER_1_TOOL=claude' <<< "$out"
grep -Fq 'VOTER_2_TOOL=codex' <<< "$out"
grep -Fq 'VOTER_3_TOOL=cursor' <<< "$out"
grep -Fq 'VOTER_2_STATUS=launched' <<< "$out"
grep -Fq 'VOTER_3_STATUS=launched' <<< "$out"
grep -Fq 'DISPATCH_OK=true' <<< "$out"
grep -Fq -- '--output-last-message' "$CODEX_LOG" || { echo "FAIL: codex launch missing output-last-message" >&2; exit 1; }
grep -Fq -- '--output-format json' "$CURSOR_LOG" || { echo "FAIL: cursor launch missing json mode" >&2; exit 1; }

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$TMP/absent" --codex-available false --cursor-available false)
grep -Fq 'VOTER_2_TOOL=claude' <<< "$out"
grep -Fq 'VOTER_3_TOOL=claude' <<< "$out"
grep -Fq 'VOTER_2_STATUS=fallback' <<< "$out"
grep -Fq 'VOTER_3_STATUS=fallback' <<< "$out"
grep -Fq 'DISPATCH_OK=true' <<< "$out"

issues_log="$TMP/execution-issues.md"
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_STUB_MODE=empty LARCH_EXECUTION_ISSUES_LOG="$issues_log" "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$TMP/empty-voter1" --codex-available true --cursor-available true)
grep -Fq 'VOTER_1_STATUS=failed' <<< "$out"
grep -Fq 'dispatch-code-voters.sh voter1' "$issues_log"
grep -Fq 'launch-claude-review.sh (claude voter) warning (exit 0)' "$issues_log"

echo "PASS: test-dispatch-code-voters.sh"
