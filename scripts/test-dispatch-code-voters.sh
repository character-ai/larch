#!/usr/bin/env bash
# Regression harness for scripts/dispatch-code-voters.sh waterfall wiring.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

# --section CLI selector: splits the 11 scenarios + 3 regression blocks into
# 8 groups so the CI matrix can pack them as independent harness rows. Sections:
#   happy:                          scenarios 1-3 (happy path, absent tools, empty voter)
#   edge-and-r3-claude:             scenarios 4-5 (symlink diff, 2 MB diff) + Regression 3 claude case
#   retry-claude:                   retry_success_claude, retry_fail_claude
#   retry-codex-success:            retry_success_codex
#   retry-cursor:                   retry_success_cursor
#   retry-codex-fail-and-fallback:  retry_fail_codex, retry_fail_fallback
#   regressions-r1-r2:              env-isolation (Regression 1) + harness-ancestor path-guard (Regression 2)
#   regressions-r3-codex:           production-shape codex case (Regression 3, codex half)
# With no --section, all 11 scenarios + 3 regressions run sequentially
# (local-dev backward compat).
SECTION=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --section) SECTION="$2"; shift 2 ;;
        *) shift ;;
    esac
done
if [[ -n "$SECTION" ]]; then
    case "$SECTION" in
        happy|edge-and-r3-claude|retry-claude|retry-codex-success|retry-cursor|retry-codex-fail-and-fallback|regressions-r1-r2|regressions-r3-codex) ;;
        *)
            printf 'ERROR: unknown --section: %s\n' "$SECTION" >&2
            exit 1
            ;;
    esac
fi
section_runs() {
    [[ -z "$SECTION" || "$SECTION" == "$1" ]]
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/dispatch-code-voters.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-dispatch-code-voters.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
unset CLAUDE_PLUGIN_ROOT
# Drop any parent /implement env vars so test invocations do not inherit the
# parent run's issues-log path and accidentally append test-fixture diagnostics
# to a live execution-issues.md.  Tests that need to assert issues-log writes
# set LARCH_EXECUTION_ISSUES_LOG explicitly on each individual invocation.
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR

STUB_BIN="$TMP/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/codex" <<'STUB'
#!/usr/bin/env bash
out=""; last=""
log="${CODEX_STUB_LOG:-}"
for arg in "$@"; do [[ "$last" == "--output-last-message" ]] && out="$arg"; last="$arg"; done
[[ -n "$out" ]] || exit 9
[[ -n "$log" ]] && printf '%s\n' "$*" >> "$log"
case "${CODEX_STUB_MODE:-ok}" in
  parse_retry_success)
    count_file="${CODEX_STUB_COUNT_FILE:?CODEX_STUB_COUNT_FILE required}"
    count=0
    [[ -f "$count_file" ]] && count=$(cat "$count_file" 2>/dev/null || echo 0)
    count=$((count + 1))
    printf '%s\n' "$count" > "$count_file"
    if [[ "$count" -eq 1 ]]; then
      printf 'Narrative codex output without structured votes.\n' > "$out"
    else
      printf 'FINDING_1: YES\n' > "$out"
    fi
    ;;
  parse_retry_fail)
    count_file="${CODEX_STUB_COUNT_FILE:?CODEX_STUB_COUNT_FILE required}"
    count=0
    [[ -f "$count_file" ]] && count=$(cat "$count_file" 2>/dev/null || echo 0)
    count=$((count + 1))
    printf '%s\n' "$count" > "$count_file"
    printf 'Narrative codex output without structured votes.\n' > "$out"
    ;;
  *)
    printf 'FINDING_1: YES\n' > "$out"
    ;;
esac
STUB
cat > "$STUB_BIN/cursor" <<'STUB'
#!/usr/bin/env bash
log="${CURSOR_STUB_LOG:-}"
[[ -n "$log" ]] && printf '%s\n' "$*" >> "$log"
case "${CURSOR_STUB_MODE:-ok}" in
  parse_retry_success)
    count_file="${CURSOR_STUB_COUNT_FILE:?CURSOR_STUB_COUNT_FILE required}"
    count=0
    [[ -f "$count_file" ]] && count=$(cat "$count_file" 2>/dev/null || echo 0)
    count=$((count + 1))
    printf '%s\n' "$count" > "$count_file"
    if [[ "$count" -eq 1 ]]; then
      printf '{"result":"Narrative cursor output without structured votes.","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
    else
      printf '{"result":"FINDING_1: NO -- cursor","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
    fi
    ;;
  parse_retry_fail)
    count_file="${CURSOR_STUB_COUNT_FILE:?CURSOR_STUB_COUNT_FILE required}"
    count=0
    [[ -f "$count_file" ]] && count=$(cat "$count_file" 2>/dev/null || echo 0)
    count=$((count + 1))
    printf '%s\n' "$count" > "$count_file"
    printf '{"result":"Narrative cursor output without structured votes.","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
    ;;
  *)
    printf '{"result":"FINDING_1: NO -- cursor","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
    ;;
esac
STUB
cat > "$STUB_BIN/claude" <<'STUB'
#!/usr/bin/env bash
cat >/dev/null
case "${CLAUDE_STUB_MODE:-ok}" in
  empty) exit 0 ;;
  fail)
    printf 'stub claude failure\n' >&2
    exit 7 ;;
  parse_retry_success)
    count_file="${CLAUDE_STUB_COUNT_FILE:?CLAUDE_STUB_COUNT_FILE required}"
    count=0
    [[ -f "$count_file" ]] && count=$(cat "$count_file" 2>/dev/null || echo 0)
    count=$((count + 1))
    printf '%s\n' "$count" > "$count_file"
    if [[ "$count" -eq 1 ]]; then
      printf 'I reviewed the ballot and here is my narrative instead of votes.\n'
    else
      printf 'FINDING_1: YES\n'
    fi
    exit 0 ;;
  parse_retry_fail)
    count_file="${CLAUDE_STUB_COUNT_FILE:?CLAUDE_STUB_COUNT_FILE required}"
    count=0
    [[ -f "$count_file" ]] && count=$(cat "$count_file" 2>/dev/null || echo 0)
    count=$((count + 1))
    printf '%s\n' "$count" > "$count_file"
    printf 'I reviewed the ballot and here is my narrative instead of votes.\n'
    exit 0 ;;
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

if section_runs happy; then
out=$(PATH="$STUB_BIN:$PATH" CODEX_STUB_LOG="$CODEX_LOG" CURSOR_STUB_LOG="$CURSOR_LOG" "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$TMP/happy" --codex-available true --cursor-available true --diff-file "$DIFF_FILE" --plan-file "$PLAN_FILE")
grep -Fq 'VOTER_1_TOOL=claude' <<< "$out"
grep -Fq 'VOTER_2_TOOL=codex' <<< "$out"
grep -Fq 'VOTER_3_TOOL=cursor' <<< "$out"
grep -Fq 'VOTER_2_STATUS=launched' <<< "$out"
grep -Fq 'VOTER_3_STATUS=launched' <<< "$out"
grep -Fq 'DISPATCH_OK=true' <<< "$out"
grep -Fq -- '--output-last-message' "$CODEX_LOG" || { echo "FAIL: codex launch missing output-last-message" >&2; exit 1; }
grep -Fq -- '--output-format json' "$CURSOR_LOG" || { echo "FAIL: cursor launch missing json mode" >&2; exit 1; }
grep -Fq 'VOTER_1_PARSE_RATE_STATUS=OK' <<< "$out" || { echo "FAIL: voter1 parse-rate status missing/incorrect" >&2; exit 1; }
grep -Fq 'VOTER_2_PARSE_RATE_STATUS=OK' <<< "$out" || { echo "FAIL: voter2 parse-rate status missing/incorrect" >&2; exit 1; }
grep -Fq 'VOTER_3_PARSE_RATE_STATUS=OK' <<< "$out" || { echo "FAIL: voter3 parse-rate status missing/incorrect" >&2; exit 1; }
[[ ! -e "$TMP/happy/claude-vote-output-first-pass.txt" && ! -e "$TMP/happy/codex-vote-output-first-pass.txt" && ! -e "$TMP/happy/cursor-vote-output-first-pass.txt" ]] \
    || { echo "FAIL: happy path must not write parse-retry first-pass sidecars" >&2; exit 1; }

grep -Fq 'Verify silently' "$TMP/happy/claude-vote-prompt.txt" || { echo "FAIL: claude vote prompt missing Verify silently directive" >&2; exit 1; }
grep -Fq 'Do not invoke any tools' "$TMP/happy/claude-vote-prompt.txt" || { echo "FAIL: claude vote prompt missing no-tools directive" >&2; exit 1; }
grep -Fq 'Output ONLY vote lines' "$TMP/happy/claude-vote-prompt.txt" || { echo "FAIL: claude vote prompt missing Output ONLY vote lines directive" >&2; exit 1; }

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$TMP/absent" --codex-available false --cursor-available false)
grep -Fq 'VOTER_2_TOOL=claude' <<< "$out"
grep -Fq 'VOTER_3_TOOL=claude' <<< "$out"
grep -Fq 'VOTER_2_STATUS=fallback' <<< "$out"
grep -Fq 'VOTER_3_STATUS=fallback' <<< "$out"
grep -Fq 'DISPATCH_OK=true' <<< "$out"

issues_log="$TMP/execution-issues.md"
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_STUB_MODE=empty LARCH_EXECUTION_ISSUES_LOG="$issues_log" "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$TMP/empty-voter1" --codex-available true --cursor-available true)
grep -Fq 'VOTER_1_STATUS=failed' <<< "$out"
grep -Fq 'VOTER_1_PARSE_RATE_STATUS=SKIPPED' <<< "$out"
grep -Fq 'dispatch-code-voters.sh voter1' "$issues_log"
grep -Fq 'launch-claude-review.sh (claude voter) failed (exit 99)' "$issues_log"
grep -Fq 'voter1_rc=99' "$issues_log"
fi  # end section: happy

if section_runs edge-and-r3-claude; then
# Voter dispatch now receives bounded regular-file copies of diff/plan context,
# so a symlink source path still yields grounded voter context without passing a
# symlink through to launch-claude-subprocess.sh.
sym_review_tmpdir="$TMP/sym-diff"
mkdir -p "$sym_review_tmpdir"
sym_diff="$TMP/diff-symlink.patch"
ln -s "$DIFF_FILE" "$sym_diff"
out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --ballot-file "$BALLOT" \
    --review-tmpdir "$sym_review_tmpdir" \
    --codex-available true \
    --cursor-available true \
    --diff-file "$sym_diff" \
    --plan-file "$PLAN_FILE")
grep -Fq 'VOTER_1_STATUS=launched' <<< "$out" \
    || { echo "FAIL: symlink-diff scenario expected VOTER_1_STATUS=launched with bounded diff copy (got: $(grep VOTER_1_STATUS <<< "$out"))" >&2; exit 1; }
grep -Fq 'DISPATCH_OK=true' <<< "$out" \
    || { echo "FAIL: symlink-diff scenario expected DISPATCH_OK=true" >&2; exit 1; }
[[ -f "$sym_review_tmpdir/diff-context.txt" ]] \
    || { echo "FAIL: symlink-diff scenario expected bounded diff copy" >&2; exit 1; }

# A 2 MB diff file must not cause the voter to fail; dispatch sends a bounded copy.
big_diff="$TMP/big-diff.txt"
dd if=/dev/zero bs=1024 count=2048 2>/dev/null | tr '\0' 'x' > "$big_diff"
big_review_tmpdir="$TMP/big-diff-review"
mkdir -p "$big_review_tmpdir"
out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --ballot-file "$BALLOT" \
    --review-tmpdir "$big_review_tmpdir" \
    --codex-available true \
    --cursor-available true \
    --diff-file "$big_diff" \
    --plan-file "$PLAN_FILE")
grep -Fq 'DISPATCH_OK=true' <<< "$out" \
    || { echo "FAIL: 2MB-diff scenario expected DISPATCH_OK=true" >&2; exit 1; }
grep -Fq 'VOTER_1_STATUS=launched' <<< "$out" \
    || { echo "FAIL: 2MB-diff scenario expected VOTER_1_STATUS=launched (got: $(grep VOTER_1_STATUS <<< "$out"))" >&2; exit 1; }
[[ -s "$big_review_tmpdir/claude-vote-output.txt" ]] \
    || { echo "FAIL: 2MB-diff scenario expected non-empty voter output" >&2; exit 1; }
[[ "$(wc -c < "$big_review_tmpdir/diff-context.txt")" -eq 200000 ]] \
    || { echo "FAIL: 2MB-diff scenario expected 200000-byte bounded diff copy" >&2; exit 1; }
grep -Fq 'FINDING_1: YES' "$big_review_tmpdir/claude-vote-output.txt" \
    || { echo "FAIL: 2MB-diff scenario expected FINDING_1: YES in voter output" >&2; exit 1; }

# Regression 3 (claude case): production-shape — review tmpdir outside any harness ancestry,
# so local diag files and the explicit issues-log must be written with tool-specific labels.
(
    prod_tmp="$(mktemp -d "${TMPDIR:-/tmp}/review-prod-shape-claude.XXXXXX")"
    trap 'rm -rf "$prod_tmp"' EXIT

    prod_issues="$prod_tmp/prod-issues.md"
    out=$(PATH="$STUB_BIN:$PATH" \
        CLAUDE_STUB_MODE=parse_retry_fail CLAUDE_STUB_COUNT_FILE="$TMP/prod-shape-count.txt" \
        LARCH_EXECUTION_ISSUES_LOG="$prod_issues" \
        "$SCRIPT" \
        --ballot-file "$BALLOT" \
        --review-tmpdir "$prod_tmp/review" \
        --codex-available true \
        --cursor-available true)
    grep -Fq 'VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE' <<< "$out" \
        || { echo "FAIL: regression3 prod-shape — expected NOT_SUBSTANTIVE parse-rate status" >&2; exit 1; }
    [[ -s "$prod_tmp/review/claude-vote-output-parse-rate-diag.txt" ]] \
        || { echo "FAIL: regression3 prod-shape — local claude diag file not written" >&2; exit 1; }
    grep -Fq 'dispatch-code-voters.sh claude' "$prod_issues" \
        || { echo "FAIL: regression3 prod-shape — claude issues-log entry missing" >&2; exit 1; }
    grep -Fq 'launch-claude-review.sh (voter parse-rate check)' "$prod_issues" \
        || { echo "FAIL: regression3 prod-shape — claude tool label missing from issues-log" >&2; exit 1; }
)
fi  # end section: edge-and-r3-claude

if section_runs retry-claude; then
retry_success_tmp="$TMP/retry-success"
retry_count_file="$TMP/retry-success-count.txt"
mkdir -p "$retry_success_tmp"
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_STUB_MODE=parse_retry_success CLAUDE_STUB_COUNT_FILE="$retry_count_file" "$SCRIPT" \
    --ballot-file "$BALLOT" \
    --review-tmpdir "$retry_success_tmp" \
    --codex-available true \
    --cursor-available true)
grep -Fq 'VOTER_1_PARSE_RATE_STATUS=OK' <<< "$out" \
    || { echo "FAIL: parse-rate retry success expected VOTER_1_PARSE_RATE_STATUS=OK" >&2; exit 1; }
grep -Fq 'FINDING_1: YES' "$retry_success_tmp/claude-vote-output.txt" \
    || { echo "FAIL: parse-rate retry success expected structured final voter output" >&2; exit 1; }
[[ -f "$retry_success_tmp/claude-vote-output-first-pass.txt" ]] \
    || { echo "FAIL: parse-rate retry success expected claude first-pass sidecar" >&2; exit 1; }
grep -Fq 'narrative instead of votes' "$retry_success_tmp/claude-vote-output-first-pass.txt" \
    || { echo "FAIL: claude first-pass sidecar should preserve pre-retry narrative output" >&2; exit 1; }
if cmp -s "$retry_success_tmp/claude-vote-output-first-pass.txt" "$retry_success_tmp/claude-vote-output.txt"; then
    echo "FAIL: claude first-pass sidecar must differ from promoted retry output" >&2
    exit 1
fi
if [[ -e "$retry_success_tmp/claude-vote-output-parse-rate-diag.txt" || -e "$retry_success_tmp/claude-parse-rate-diag.txt" ]]; then
    echo "FAIL: parse-rate retry success should clear claude parse-rate diag" >&2
    exit 1
fi
[[ "$(cat "$retry_count_file")" -eq 2 ]] \
    || { echo "FAIL: parse-rate retry success expected exactly two claude attempts" >&2; exit 1; }
[[ ! -e "$retry_success_tmp/claude-vote-output-parse-retry.txt" && ! -e "$retry_success_tmp/claude-vote-output-parse-retry.txt.launcher-stderr" ]] \
    || { echo "FAIL: parse-rate retry success should clean retry temp files" >&2; exit 1; }
if [[ -f "$retry_success_tmp/execution-issues.md" ]] && grep -Fq 'dispatch-code-voters.sh claude' "$retry_success_tmp/execution-issues.md"; then
    echo "FAIL: parse-rate retry success should not leave a stale execution issue warning" >&2
    exit 1
fi

retry_fail_tmp="$TMP/retry-fail"
retry_fail_count_file="$TMP/retry-fail-count.txt"
mkdir -p "$retry_fail_tmp"
# No LARCH_EXECUTION_ISSUES_LOG. For this harness-shaped REVIEW_TMPDIR, the parse-rate
# guard skips append-tool-failure.sh entirely, so stderr and the local diag sidecar
# remain the only warning surfaces.
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_STUB_MODE=parse_retry_fail CLAUDE_STUB_COUNT_FILE="$retry_fail_count_file" "$SCRIPT" \
    --ballot-file "$BALLOT" \
    --review-tmpdir "$retry_fail_tmp" \
    --codex-available true \
    --cursor-available true)
grep -Fq 'VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE' <<< "$out" \
    || { echo "FAIL: parse-rate retry failure expected VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" >&2; exit 1; }
grep -Fq 'narrative instead of votes' "$retry_fail_tmp/claude-vote-output.txt" \
    || { echo "FAIL: parse-rate retry failure should preserve original narrative output" >&2; exit 1; }
[[ -s "$retry_fail_tmp/claude-vote-output-parse-rate-diag.txt" ]] \
    || { echo "FAIL: parse-rate retry failure should preserve claude parse-rate diag" >&2; exit 1; }
grep -Fq "voter_file=$retry_fail_tmp/claude-vote-output.txt" "$retry_fail_tmp/claude-vote-output-parse-rate-diag.txt" \
    || { echo "FAIL: parse-rate retry failure diag should bind to the canonical claude voter output" >&2; exit 1; }
[[ "$(cat "$retry_fail_count_file")" -eq 2 ]] \
    || { echo "FAIL: parse-rate retry failure expected exactly two claude attempts" >&2; exit 1; }
[[ ! -e "$retry_fail_tmp/claude-vote-output-parse-retry.txt" && ! -e "$retry_fail_tmp/claude-vote-output-parse-retry.txt.launcher-stderr" ]] \
    || { echo "FAIL: parse-rate retry failure should clean retry temp files" >&2; exit 1; }
[[ ! -e "$retry_fail_tmp/claude-vote-output-first-pass.txt" ]] \
    || { echo "FAIL: parse-rate retry failure must not write first-pass sidecar" >&2; exit 1; }
fi  # end section: retry-claude

if section_runs retry-codex-success; then
retry_success_codex_tmp="$TMP/retry-success-codex"
retry_success_codex_count_file="$TMP/retry-success-codex-count.txt"
out=$(PATH="$STUB_BIN:$PATH" CODEX_STUB_MODE=parse_retry_success CODEX_STUB_COUNT_FILE="$retry_success_codex_count_file" "$SCRIPT" \
    --ballot-file "$BALLOT" \
    --review-tmpdir "$retry_success_codex_tmp" \
    --codex-available true \
    --cursor-available true)
grep -Fq 'VOTER_2_TOOL=codex' <<< "$out" \
    || { echo "FAIL: codex retry fixture expected voter 2 to stay on codex" >&2; exit 1; }
grep -Fq 'VOTER_2_PARSE_RATE_STATUS=OK' <<< "$out" \
    || { echo "FAIL: codex parse-rate retry success expected VOTER_2_PARSE_RATE_STATUS=OK" >&2; exit 1; }
grep -Fq 'FINDING_1: YES' "$retry_success_codex_tmp/codex-vote-output.txt" \
    || { echo "FAIL: codex parse-rate retry success expected structured final voter output" >&2; exit 1; }
[[ -f "$retry_success_codex_tmp/codex-vote-output-first-pass.txt" ]] \
    || { echo "FAIL: codex parse-rate retry success expected first-pass sidecar" >&2; exit 1; }
grep -Fq 'Narrative codex output without structured votes' "$retry_success_codex_tmp/codex-vote-output-first-pass.txt" \
    || { echo "FAIL: codex first-pass sidecar should preserve pre-retry narrative output" >&2; exit 1; }
if cmp -s "$retry_success_codex_tmp/codex-vote-output-first-pass.txt" "$retry_success_codex_tmp/codex-vote-output.txt"; then
    echo "FAIL: codex first-pass sidecar must differ from promoted retry output" >&2
    exit 1
fi
if [[ -e "$retry_success_codex_tmp/codex-vote-output-parse-rate-diag.txt" || -e "$retry_success_codex_tmp/codex-parse-rate-diag.txt" ]]; then
    echo "FAIL: codex parse-rate retry success should clear slot-specific parse-rate diag" >&2
    exit 1
fi
[[ "$(cat "$retry_success_codex_count_file")" -eq 2 ]] \
    || { echo "FAIL: codex parse-rate retry success expected exactly two codex attempts" >&2; exit 1; }
fi  # end section: retry-codex-success

if section_runs retry-cursor; then
retry_success_cursor_tmp="$TMP/retry-success-cursor"
retry_success_cursor_count_file="$TMP/retry-success-cursor-count.txt"
out=$(PATH="$STUB_BIN:$PATH" CURSOR_STUB_MODE=parse_retry_success CURSOR_STUB_COUNT_FILE="$retry_success_cursor_count_file" "$SCRIPT" \
    --ballot-file "$BALLOT" \
    --review-tmpdir "$retry_success_cursor_tmp" \
    --codex-available true \
    --cursor-available true)
grep -Fq 'VOTER_3_TOOL=cursor' <<< "$out" \
    || { echo "FAIL: cursor retry fixture expected voter 3 to stay on cursor" >&2; exit 1; }
grep -Fq 'VOTER_3_PARSE_RATE_STATUS=OK' <<< "$out" \
    || { echo "FAIL: cursor parse-rate retry success expected VOTER_3_PARSE_RATE_STATUS=OK" >&2; exit 1; }
grep -Fq 'FINDING_1: NO -- cursor' "$retry_success_cursor_tmp/cursor-vote-output.txt" \
    || { echo "FAIL: cursor parse-rate retry success expected structured final voter output" >&2; exit 1; }
[[ -f "$retry_success_cursor_tmp/cursor-vote-output-first-pass.txt" ]] \
    || { echo "FAIL: cursor parse-rate retry success expected first-pass sidecar" >&2; exit 1; }
grep -Fq 'Narrative cursor output without structured votes' "$retry_success_cursor_tmp/cursor-vote-output-first-pass.txt" \
    || { echo "FAIL: cursor first-pass sidecar should preserve pre-retry narrative output" >&2; exit 1; }
if cmp -s "$retry_success_cursor_tmp/cursor-vote-output-first-pass.txt" "$retry_success_cursor_tmp/cursor-vote-output.txt"; then
    echo "FAIL: cursor first-pass sidecar must differ from promoted retry output" >&2
    exit 1
fi
if [[ -e "$retry_success_cursor_tmp/cursor-vote-output-parse-rate-diag.txt" || -e "$retry_success_cursor_tmp/cursor-parse-rate-diag.txt" ]]; then
    echo "FAIL: cursor parse-rate retry success should clear slot-specific parse-rate diag" >&2
    exit 1
fi
[[ "$(cat "$retry_success_cursor_count_file")" -eq 2 ]] \
    || { echo "FAIL: cursor parse-rate retry success expected exactly two cursor attempts" >&2; exit 1; }
fi  # end section: retry-cursor

if section_runs retry-codex-fail-and-fallback; then
retry_fail_codex_tmp="$TMP/retry-fail-codex"
retry_fail_codex_count_file="$TMP/retry-fail-codex-count.txt"
mkdir -p "$retry_fail_codex_tmp"
# No LARCH_EXECUTION_ISSUES_LOG. For this harness-shaped codex fixture too, the
# parse-rate guard skips append-tool-failure.sh entirely instead of appending to a
# review-local execution-issues.md fallback.
out=$(PATH="$STUB_BIN:$PATH" CODEX_STUB_MODE=parse_retry_fail CODEX_STUB_COUNT_FILE="$retry_fail_codex_count_file" "$SCRIPT" \
    --ballot-file "$BALLOT" \
    --review-tmpdir "$retry_fail_codex_tmp" \
    --codex-available true \
    --cursor-available true)
grep -Fq 'VOTER_2_PARSE_RATE_STATUS=NOT_SUBSTANTIVE' <<< "$out" \
    || { echo "FAIL: codex parse-rate retry failure expected VOTER_2_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" >&2; exit 1; }
grep -Fq 'DEGRADED_PANEL_WARNING=**⚠ Degraded code-review panel: 2/3 effective judges produced output.**' <<< "$out" \
    || { echo "FAIL: codex parse-rate retry failure should degrade effective judges" >&2; exit 1; }
[[ -s "$retry_fail_codex_tmp/codex-vote-output-parse-rate-diag.txt" ]] \
    || { echo "FAIL: codex parse-rate retry failure should preserve codex parse-rate diag" >&2; exit 1; }
[[ ! -e "$retry_fail_codex_tmp/codex-vote-output-parse-retry.txt" && ! -e "$retry_fail_codex_tmp/codex-vote-output-parse-retry.txt.launcher-stderr" ]] \
    || { echo "FAIL: codex parse-rate retry failure should clean retry temp files" >&2; exit 1; }
[[ ! -e "$retry_fail_codex_tmp/codex-vote-output-first-pass.txt" ]] \
    || { echo "FAIL: codex parse-rate retry failure must not write first-pass sidecar" >&2; exit 1; }

retry_fail_fallback_tmp="$TMP/retry-fail-fallback-claude"
retry_fail_fallback_count_file="$TMP/retry-fail-fallback-claude-count.txt"
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_STUB_MODE=parse_retry_fail CLAUDE_STUB_COUNT_FILE="$retry_fail_fallback_count_file" "$SCRIPT" \
    --ballot-file "$BALLOT" \
    --review-tmpdir "$retry_fail_fallback_tmp" \
    --codex-available false \
    --cursor-available false)
grep -Fq 'VOTER_2_TOOL=claude' <<< "$out" \
    || { echo "FAIL: fallback-claude fixture expected voter 2 to run on claude" >&2; exit 1; }
grep -Fq 'VOTER_2_PARSE_RATE_STATUS=NOT_SUBSTANTIVE' <<< "$out" \
    || { echo "FAIL: fallback-claude fixture expected VOTER_2_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" >&2; exit 1; }
grep -Fq "VOTER_2_PATH=$retry_fail_fallback_tmp/codex-vote-output-phase3.txt" <<< "$out" \
    || { echo "FAIL: fallback-claude fixture expected voter 2 final path to remain the phase3 output" >&2; exit 1; }
[[ -s "$retry_fail_fallback_tmp/codex-vote-output-phase3-parse-rate-diag.txt" ]] \
    || { echo "FAIL: fallback-claude fixture should write an output-specific codex voter diag" >&2; exit 1; }
grep -Fq "voter_file=$retry_fail_fallback_tmp/codex-vote-output-phase3.txt" "$retry_fail_fallback_tmp/codex-vote-output-phase3-parse-rate-diag.txt" \
    || { echo "FAIL: fallback-claude fixture diag should bind to the phase3 codex slot output path" >&2; exit 1; }
fi  # end section: retry-codex-fail-and-fallback

if section_runs regressions-r1-r2; then
# Regression 1: env isolation — LARCH_EXECUTION_ISSUES_LOG set on invocation, but the
# review tmpdir lives under a test-dispatch-code-voters.* harness ancestor, so the guard
# must suppress the parent issues-log write while still writing the local diag sidecar.
env_isolation_parent="$TMP/env-isolation-parent.md"
rm -f "$env_isolation_parent"
env_isolation_count="$TMP/env-isolation-count.txt"
out=$(PATH="$STUB_BIN:$PATH" \
    CLAUDE_STUB_MODE=parse_retry_fail CLAUDE_STUB_COUNT_FILE="$env_isolation_count" \
    LARCH_EXECUTION_ISSUES_LOG="$env_isolation_parent" \
    "$SCRIPT" \
    --ballot-file "$BALLOT" \
    --review-tmpdir "$TMP/env-isolation-review" \
    --codex-available true \
    --cursor-available true)
grep -Fq 'VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE' <<< "$out" \
    || { echo "FAIL: regression1 — expected NOT_SUBSTANTIVE parse-rate status" >&2; exit 1; }
if [[ -s "$env_isolation_parent" ]]; then
    echo "FAIL: regression1 env-isolation — parent LARCH_EXECUTION_ISSUES_LOG was written despite test-tmpdir voter_path" >&2
    exit 1
fi

# Regression 2: harness-ancestor path guard — diag file written locally but the explicit
# parent issues-log remains untouched for review tmpdirs nested under the harness tmp root.
path_guard_issues="$TMP/path-guard-issues.md"
rm -f "$path_guard_issues"
path_guard_review="$TMP/path-guard-review"
out=$(PATH="$STUB_BIN:$PATH" \
    CLAUDE_STUB_MODE=parse_retry_fail CLAUDE_STUB_COUNT_FILE="$TMP/path-guard-count.txt" \
    LARCH_EXECUTION_ISSUES_LOG="$path_guard_issues" \
    "$SCRIPT" \
    --ballot-file "$BALLOT" \
    --review-tmpdir "$path_guard_review" \
    --codex-available true \
    --cursor-available true)
[[ -s "$path_guard_review/claude-vote-output-parse-rate-diag.txt" ]] \
    || { echo "FAIL: regression2 path-guard — local diag file not written" >&2; exit 1; }
if [[ -s "$path_guard_issues" ]]; then
    echo "FAIL: regression2 path-guard — append-tool-failure.sh was called despite test-tmpdir voter_path" >&2
    exit 1
fi
fi  # end section: regressions-r1-r2

if section_runs regressions-r3-codex; then
# Regression 3 (codex case): production-shape — review tmpdir outside any harness ancestry,
# so local diag files and the explicit issues-log must be written with tool-specific labels.
(
    prod_tmp="$(mktemp -d "${TMPDIR:-/tmp}/review-prod-shape-codex.XXXXXX")"
    trap 'rm -rf "$prod_tmp"' EXIT

    prod_codex_issues="$prod_tmp/prod-codex-issues.md"
    out=$(PATH="$STUB_BIN:$PATH" \
        CODEX_STUB_MODE=parse_retry_fail CODEX_STUB_COUNT_FILE="$TMP/prod-shape-codex-count.txt" \
        LARCH_EXECUTION_ISSUES_LOG="$prod_codex_issues" \
        "$SCRIPT" \
        --ballot-file "$BALLOT" \
        --review-tmpdir "$prod_tmp/review-codex" \
        --codex-available true \
        --cursor-available true)
    grep -Fq 'VOTER_2_PARSE_RATE_STATUS=NOT_SUBSTANTIVE' <<< "$out" \
        || { echo "FAIL: regression3 prod-shape codex — expected NOT_SUBSTANTIVE parse-rate status" >&2; exit 1; }
    [[ -s "$prod_tmp/review-codex/codex-vote-output-parse-rate-diag.txt" ]] \
        || { echo "FAIL: regression3 prod-shape codex — local codex diag file not written" >&2; exit 1; }
    grep -Fq 'dispatch-code-voters.sh codex' "$prod_codex_issues" \
        || { echo "FAIL: regression3 prod-shape codex — issues-log entry missing" >&2; exit 1; }
    grep -Fq 'launch-review.sh --tool codex (voter parse-rate check)' "$prod_codex_issues" \
        || { echo "FAIL: regression3 prod-shape codex — codex tool label missing from issues-log" >&2; exit 1; }
)
fi  # end section: regressions-r3-codex

echo "PASS: test-dispatch-code-voters.sh"
