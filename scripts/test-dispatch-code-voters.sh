#!/usr/bin/env bash
# Regression harness for scripts/dispatch-code-voters.sh waterfall wiring.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

# --section CLI selector: splits the 12 scenarios + 3 regression blocks into
# 8 groups so the CI matrix can pack them as independent harness rows. Sections:
#   happy:                          scenarios 1-4 (happy path, absent tools, empty voter, round-2 3-judge parity)
#   edge-and-r3-claude:             scenarios 4-5 (symlink diff, 2 MB diff) + Regression 3 claude case
#   retry-claude:                   retry_success_claude, retry_fail_claude
#   retry-codex-success:            retry_success_codex
#   retry-cursor:                   retry_success_cursor
#   retry-codex-fail-and-fallback:  retry_fail_codex, retry_fail_fallback
#   regressions-r1-r2:              env-isolation (Regression 1) + harness-ancestor path-guard (Regression 2)
#   regressions-r3-codex:           production-shape codex case (Regression 3, codex half)
# With no --section, all 12 scenarios + 3 regressions run sequentially
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

require_voter_paths_file_nonempty() {
    local ctx="$1" out="$2"
    grep -Fq 'VOTER_PATHS_FILE=' <<< "$out" || { echo "FAIL: $ctx missing VOTER_PATHS_FILE KV" >&2; exit 1; }
    local f
    f=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_PATHS_FILE"{print substr($0,index($0,"=")+1);exit}')
    [[ -f "$f" && -s "$f" ]] || { echo "FAIL: $ctx VOTER_PATHS_FILE not a non-empty file: $f" >&2; exit 1; }
}

make_wait_barrier_plugin_root() {
    local root="$1"
    mkdir -p "$root/scripts" "$root/skills/shared/scripts"
    ln -sf "$REPO_ROOT/scripts/wait-for-reviewers.sh" "$root/scripts/wait-for-reviewers.sh"
    cat > "$root/skills/shared/scripts/render-voter-prompt.sh" <<'STUB_RENDER'
#!/usr/bin/env bash
printf 'stub voter prompt\n'
STUB_RENDER
    chmod +x "$root/skills/shared/scripts/render-voter-prompt.sh"
    cat > "$root/scripts/dispatch-with-waterfall.sh" <<'STUB_WATERFALL'
#!/usr/bin/env bash
set -euo pipefail
review_tmpdir="$(dirname "${LARCH_WAIT_BARRIER_VOTER2:?}")"
case "${LARCH_WAIT_BARRIER_MODE:-delayed}" in
    delayed)
        printf 'FINDING_1: YES\n' > "$LARCH_WAIT_BARRIER_VOTER2"
        printf 'FINDING_1: NO\n' > "$LARCH_WAIT_BARRIER_VOTER3"
        (
            sleep "${LARCH_WAIT_BARRIER_DELAY:-0.2}"
            printf '0\n' > "${LARCH_WAIT_BARRIER_VOTER2}.done"
            printf '0\n' > "${LARCH_WAIT_BARRIER_VOTER3}.done"
        ) >/dev/null 2>&1 &
        ;;
    immediate)
        printf 'FINDING_1: YES\n' > "$LARCH_WAIT_BARRIER_VOTER2"
        printf '0\n' > "${LARCH_WAIT_BARRIER_VOTER2}.done"
        printf 'FINDING_1: NO\n' > "$LARCH_WAIT_BARRIER_VOTER3"
        printf '0\n' > "${LARCH_WAIT_BARRIER_VOTER3}.done"
        ;;
    nonzero_done)
        printf 'FINDING_1: YES\n' > "$LARCH_WAIT_BARRIER_VOTER2"
        printf '7\n' > "${LARCH_WAIT_BARRIER_VOTER2}.done"
        printf 'FINDING_1: NO\n' > "$LARCH_WAIT_BARRIER_VOTER3"
        printf '9\n' > "${LARCH_WAIT_BARRIER_VOTER3}.done"
        ;;
    timeout)
        : > "$review_tmpdir/timeout-mode-observed"
        ;;
esac
printf 'ALL_OUTPUT_FILES=%s %s\n' "$LARCH_WAIT_BARRIER_VOTER2" "$LARCH_WAIT_BARRIER_VOTER3"
printf 'ALL_OUTPUT_TOOLS=codex cursor\n'
printf 'DISPATCH_OK=true\n'
STUB_WATERFALL
    chmod +x "$root/scripts/dispatch-with-waterfall.sh"
}

make_wait_usage_error_plugin_root() {
    local root="$1"
    make_wait_barrier_plugin_root "$root"
    cat > "$root/scripts/wait-for-reviewers.sh" <<'STUB_WAIT'
#!/usr/bin/env bash
printf 'usage: forced test wait failure\n' >&2
exit 1
STUB_WAIT
    chmod +x "$root/scripts/wait-for-reviewers.sh"
}

make_voter1_delayed_done_plugin_root() {
    local root="$1"
    mkdir -p "$root/scripts" "$root/skills/shared/scripts"
    ln -sf "$REPO_ROOT/scripts/lib-quiet.sh" "$root/scripts/lib-quiet.sh"
    ln -sf "$REPO_ROOT/scripts/lib-voter-parse-rate.sh" "$root/scripts/lib-voter-parse-rate.sh"
    ln -sf "$REPO_ROOT/scripts/parse-judge-vote-and-rating.sh" "$root/scripts/parse-judge-vote-and-rating.sh"
    ln -sf "$REPO_ROOT/scripts/wait-for-reviewers.sh" "$root/scripts/wait-for-reviewers.sh"
    ln -sf "$REPO_ROOT/scripts/dispatch-code-voters.sh" "$root/scripts/dispatch-code-voters.sh"
    cat > "$root/skills/shared/scripts/render-voter-prompt.sh" <<'STUB_RENDER'
#!/usr/bin/env bash
printf 'stub voter prompt\n'
STUB_RENDER
    chmod +x "$root/skills/shared/scripts/render-voter-prompt.sh"
    cat > "$root/scripts/launch-claude-review.sh" <<'STUB_CLAUDE'
#!/usr/bin/env bash
set -euo pipefail
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output|--output-file) output="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
[[ -n "$output" ]] || exit 2
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\n' > "$output"
if [[ "${LARCH_VOTER1_DONE_MODE:-delayed}" != "missing" ]]; then
    (
        sleep "${LARCH_VOTER1_DONE_DELAY:-1}"
        printf '0\n' > "${output}.done"
    ) >/dev/null 2>&1 &
fi
exit 0
STUB_CLAUDE
    chmod +x "$root/scripts/launch-claude-review.sh"
    cat > "$root/scripts/dispatch-with-waterfall.sh" <<'STUB_WATERFALL'
#!/usr/bin/env bash
set -euo pipefail
review_tmpdir=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --slots-file)
            review_tmpdir="$(dirname "${2:?}")"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done
[[ -n "$review_tmpdir" ]] || exit 2
v2="$review_tmpdir/codex-vote-output.txt"
v3="$review_tmpdir/cursor-vote-output.txt"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\n' > "$v2"
printf '0\n' > "${v2}.done"
printf 'FINDING_1: NO CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\n' > "$v3"
printf '0\n' > "${v3}.done"
printf 'ALL_OUTPUT_FILES=%s %s\n' "$v2" "$v3"
printf 'ALL_OUTPUT_TOOLS=codex cursor\n'
printf 'DISPATCH_OK=true\n'
STUB_WATERFALL
    chmod +x "$root/scripts/dispatch-with-waterfall.sh"
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
  delayed_done_race)
    printf 'FINDING_1: YES -- codex delayed\n' > "$out"
    sleep "${CODEX_STUB_DELAY:-1}"
    ;;
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
  delayed_done_race)
    printf '{"result":"FINDING_1: NO -- cursor delayed","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
    sleep "${CURSOR_STUB_DELAY:-1}"
    ;;
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
  fail_nonempty)
    printf 'stub voter output for diag test\n'
    exit 7 ;;
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
require_voter_paths_file_nonempty "happy-r1" "$out"
r1pf=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_PATHS_FILE"{print substr($0,index($0,"=")+1);exit}')
[[ $(wc -l < "$r1pf" | tr -d ' ') -eq 3 ]] || { echo "FAIL: round1 code-voter paths file expects 3 lines" >&2; exit 1; }

for prompt in "$TMP/happy/claude-vote-prompt.txt" "$TMP/happy/codex-vote-prompt.txt" "$TMP/happy/cursor-vote-prompt.txt"; do
grep -Fq 'Verify silently' "$prompt" || { echo "FAIL: $(basename "$prompt") missing Verify silently directive" >&2; exit 1; }
grep -Fq 'You may read the ballot file and any provided diff/plan context files for verification' "$prompt" || { echo "FAIL: $(basename "$prompt") missing bounded file-read verification directive" >&2; exit 1; }
grep -Fq 'Output ONLY vote lines' "$prompt" || { echo "FAIL: $(basename "$prompt") missing Output ONLY vote lines directive" >&2; exit 1; }
grep -Fq 'fix proposals are informational; the coder decides the exact change' "$prompt" || { echo "FAIL: $(basename "$prompt") missing informational-fix voter guardrail" >&2; exit 1; }
grep -Fq 'dislike or distrust the proposed fix' "$prompt" || { echo "FAIL: $(basename "$prompt") missing dislike/distrust NO-vote guardrail" >&2; exit 1; }
grep -Fq "For \`OOS_N:\` items" "$prompt" \
    || { echo "FAIL: $(basename "$prompt") missing canonical OOS_N clause" >&2; exit 1; }
grep -Fq 'vote based on whether the **problem described** is real, concrete, and worth filing as a GitHub issue.' "$prompt" \
    || { echo "FAIL: $(basename "$prompt") missing OOS problem-vs-solution body" >&2; exit 1; }
grep -Fq 'FINDING_N: YES CORRECTNESS=<true|partially-true|false-positive|uncertain>' "$prompt" || { echo "FAIL: $(basename "$prompt") missing rated FINDING_N example" >&2; exit 1; }
grep -Fq 'OOS_N: YES CORRECTNESS=<true|partially-true|false-positive|uncertain>' "$prompt" || { echo "FAIL: $(basename "$prompt") missing rated OOS_N example" >&2; exit 1; }
grep -Fq 'Lines that do not start with the exact ballot ID from the ballot heading (FINDING_N: or OOS_N:) followed by YES, NO, or EXONERATE are silently ignored.' "$prompt" \
    || { echo "FAIL: $(basename "$prompt") missing dual-prefix ignore rule" >&2; exit 1; }
done

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$TMP/absent" --codex-available false --cursor-available false)
grep -Fq 'VOTER_2_TOOL=claude' <<< "$out"
grep -Fq 'VOTER_3_TOOL=claude' <<< "$out"
grep -Fq 'VOTER_2_STATUS=fallback' <<< "$out"
grep -Fq 'VOTER_3_STATUS=fallback' <<< "$out"
grep -Fq 'DISPATCH_OK=true' <<< "$out"

require_voter_paths_file_nonempty "happy-absent" "$out"

issues_log="$TMP/execution-issues.md"
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_STUB_MODE=empty LARCH_EXECUTION_ISSUES_LOG="$issues_log" "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$TMP/empty-voter1" --codex-available true --cursor-available true)
grep -Fq 'VOTER_1_STATUS=failed' <<< "$out"
grep -Fq 'VOTER_1_PARSE_RATE_STATUS=SKIPPED' <<< "$out"
grep -Fq 'dispatch-code-voters.sh voter1' "$issues_log"
grep -Fq 'launch-claude-review.sh (claude voter) failed (exit 99)' "$issues_log"
grep -Fq 'voter1_rc=99' "$issues_log"

require_voter_paths_file_nonempty "happy-empty-voter1" "$out"

issues_log_nonempty="$TMP/execution-issues-nonempty.md"
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_STUB_MODE=fail_nonempty LARCH_EXECUTION_ISSUES_LOG="$issues_log_nonempty" "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$TMP/nonempty-voter1" --codex-available true --cursor-available true)
grep -Fq 'VOTER_1_STATUS=failed' <<< "$out"
grep -Fq -- '--- first 200 bytes of voter output ---' "$issues_log_nonempty"
grep -Fq 'stub voter output for diag test' "$issues_log_nonempty"

require_voter_paths_file_nonempty "happy-nonempty-voter1" "$out"

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$TMP/round2" --codex-available true --cursor-available true --round-num 2)
grep -Fq 'VOTER_1_TOOL=claude' <<< "$out"
grep -Fq 'VOTER_2_TOOL=codex' <<< "$out"
grep -Fq 'VOTER_3_TOOL=cursor' <<< "$out"
case "$out" in
    *VOTER_2_STATUS=skipped*) echo "FAIL: round2 must not skip voter 2 (Codex stays on rounds 2+)" >&2; exit 1 ;;
esac
grep -Fq 'VOTER_2_STATUS=launched' <<< "$out" || grep -Fq 'VOTER_2_STATUS=fallback' <<< "$out" \
    || { echo "FAIL: round2 voter 2 must be launched or fallback, not skipped" >&2; exit 1; }
grep -Fq 'VOTER_2_PARSE_RATE_STATUS=OK' <<< "$out" || { echo "FAIL: round2 voter2 parse-rate status missing/incorrect" >&2; exit 1; }
grep -Fq 'VOTER_3_STATUS=launched' <<< "$out" || grep -Fq 'VOTER_3_STATUS=fallback' <<< "$out" \
    || { echo "FAIL: round2 voter 3 must be launched or fallback" >&2; exit 1; }
grep -Fq 'DISPATCH_OK=true' <<< "$out"
if grep -Fq 'DEGRADED_PANEL_WARNING=' <<< "$out"; then
    echo "FAIL: round2 should not emit a degraded panel warning when all three effective judges produce output" >&2
    exit 1
fi
[[ "$(wc -l < "$TMP/round2/code-voter-slots.ndjson")" -eq 2 ]] \
    || { echo "FAIL: round2 manifest must contain voter-2 and voter-3 slots" >&2; exit 1; }
grep -Fq '"slot":"voter-2"' "$TMP/round2/code-voter-slots.ndjson" \
    || { echo "FAIL: round2 manifest missing voter-2 slot" >&2; exit 1; }
grep -Fq '"slot":"voter-3"' "$TMP/round2/code-voter-slots.ndjson" \
    || { echo "FAIL: round2 manifest missing voter-3 slot" >&2; exit 1; }
grep -Fq '3-judge voting panel' "$TMP/round2/claude-vote-prompt.txt" \
    || { echo "FAIL: round2 claude voter prompt must describe a 3-judge voting panel" >&2; exit 1; }
require_voter_paths_file_nonempty "happy-round2" "$out"
r2pf=$(printf '%s\n' "$out" | awk -F= '$1=="VOTER_PATHS_FILE"{print substr($0,index($0,"=")+1);exit}')
[[ $(wc -l < "$r2pf" | tr -d ' ') -eq 3 ]] || { echo "FAIL: round2 code-voter paths file expects 3 lines" >&2; exit 1; }

wait_plugin="$TMP/wait-plugin"
make_wait_barrier_plugin_root "$wait_plugin"
wait_tmp="$TMP/wait-delayed"
mkdir -p "$wait_tmp"
wait_start=$(date +%s)
out=$(PATH="$STUB_BIN:$PATH" \
    CLAUDE_PLUGIN_ROOT="$wait_plugin" \
    WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05 \
    LARCH_VOTER_WAIT_TIMEOUT=2 \
    LARCH_WAIT_BARRIER_DELAY=1 \
    LARCH_WAIT_BARRIER_VOTER2="$wait_tmp/codex-vote-output.txt" \
    LARCH_WAIT_BARRIER_VOTER3="$wait_tmp/cursor-vote-output.txt" \
    "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$wait_tmp" --codex-available true --cursor-available true)
wait_end=$(date +%s)
grep -Fq 'VOTER_2_STATUS=launched' <<< "$out" \
    || { echo "FAIL: delayed .done wait gate expected voter2 launched (got: $(grep VOTER_2_STATUS <<< "$out"))" >&2; exit 1; }
grep -Fq 'VOTER_3_STATUS=launched' <<< "$out" \
    || { echo "FAIL: delayed .done wait gate expected voter3 launched (got: $(grep VOTER_3_STATUS <<< "$out"))" >&2; exit 1; }
if (( wait_end - wait_start < 1 )); then
    echo "FAIL: delayed .done wait gate returned before delayed sentinels could be written" >&2
    exit 1
fi

wait_immediate_tmp="$TMP/wait-immediate"
mkdir -p "$wait_immediate_tmp"
out=$(PATH="$STUB_BIN:$PATH" \
    CLAUDE_PLUGIN_ROOT="$wait_plugin" \
    WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05 \
    LARCH_VOTER_WAIT_TIMEOUT=2 \
    LARCH_WAIT_BARRIER_MODE=immediate \
    LARCH_WAIT_BARRIER_VOTER2="$wait_immediate_tmp/codex-vote-output.txt" \
    LARCH_WAIT_BARRIER_VOTER3="$wait_immediate_tmp/cursor-vote-output.txt" \
    "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$wait_immediate_tmp" --codex-available true --cursor-available true)
grep -Fq 'DISPATCH_OK=true' <<< "$out" \
    || { echo "FAIL: immediate wait gate should survive normal _wait_rc=0 path" >&2; exit 1; }
grep -Fq 'VOTER_2_STATUS=launched' <<< "$out" \
    || { echo "FAIL: immediate wait gate expected voter2 launched" >&2; exit 1; }

hook_d5="$TMP/case-dispatch-hook.hook"
printf 'exit 143\n' > "$hook_d5"
hook_review_tmp="$TMP/hook-review"
# set +e: on bash 5.x (Linux), out=$(cmd exiting 143) under set -e exits the
# test. Capture the exit code separately so we can assert on output regardless.
set +e
out=$(PATH="$STUB_BIN:$PATH" \
    LARCH_ALLOW_TEST_HOOKS=1 \
    LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE="$hook_d5" \
    LARCH_VOTER_WAIT_TIMEOUT=2 \
    "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$hook_review_tmp" --codex-available false --cursor-available true)
set -e
grep -Fq 'VOTER_3_STATUS=launched' <<< "$out" \
    || { echo "FAIL: launch-review hook path should still publish voter3 done/output before dispatch tallies" >&2; exit 1; }
grep -Fq 'VOTER_3_PARSE_RATE_STATUS=NOT_SUBSTANTIVE' <<< "$out" \
    || { echo "FAIL: launch-review hook path should surface raw cursor JSON as NOT_SUBSTANTIVE instead of failed" >&2; exit 1; }
# cursor-vote-output.txt holds the raw JSON bytes because launch-review.sh
# exits via the hook before its jq extraction step; assert the raw result field.
grep -Fq '"result":"FINDING_1: NO -- cursor"' "$hook_review_tmp/cursor-vote-output.txt" \
    || { echo "FAIL: launch-review hook path should preserve raw cursor JSON output for the parse-rate check" >&2; exit 1; }
require_voter_paths_file_nonempty "happy-launch-review-hook" "$out"

prod_delay_tmp="$TMP/cursor-prod-delay"
mkdir -p "$prod_delay_tmp"
prod_delay_start=$(date +%s)
out=$(PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_MODE=delayed_done_race \
    CURSOR_STUB_DELAY=1 \
    "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$prod_delay_tmp" --codex-available false --cursor-available true)
prod_delay_end=$(date +%s)
grep -Fq 'VOTER_3_TOOL=cursor' <<< "$out" \
    || { echo "FAIL: production delayed .done path should keep voter3 on cursor" >&2; exit 1; }
grep -Fq 'VOTER_3_STATUS=launched' <<< "$out" \
    || { echo "FAIL: production delayed .done path should keep voter3 launched" >&2; exit 1; }
grep -Fq 'VOTER_3_PARSE_RATE_STATUS=OK' <<< "$out" \
    || { echo "FAIL: production delayed .done path should keep the post-processed cursor output parseable" >&2; exit 1; }
grep -Fq 'FINDING_1: NO -- cursor delayed' "$prod_delay_tmp/cursor-vote-output.txt" \
    || { echo "FAIL: production delayed .done path should preserve the extracted cursor result after post-processing" >&2; exit 1; }
if (( prod_delay_end - prod_delay_start < 1 )); then
    echo "FAIL: production delayed .done path returned before launch-review.sh could promote the delayed cursor sentinel" >&2
    exit 1
fi
require_voter_paths_file_nonempty "happy-cursor-prod-delay" "$out"

prod_codex_delay_tmp="$TMP/codex-prod-delay"
mkdir -p "$prod_codex_delay_tmp"
prod_codex_delay_start=$(date +%s)
out=$(PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_MODE=delayed_done_race \
    CODEX_STUB_DELAY=1 \
    "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$prod_codex_delay_tmp" --codex-available true --cursor-available false)
prod_codex_delay_end=$(date +%s)
grep -Fq 'VOTER_2_TOOL=codex' <<< "$out" \
    || { echo "FAIL: production delayed .done path should keep voter2 on codex" >&2; exit 1; }
grep -Fq 'VOTER_2_STATUS=launched' <<< "$out" \
    || { echo "FAIL: production delayed .done path should keep voter2 launched" >&2; exit 1; }
grep -Fq 'VOTER_2_PARSE_RATE_STATUS=OK' <<< "$out" \
    || { echo "FAIL: production delayed .done path should keep the codex output parseable" >&2; exit 1; }
grep -Fq 'FINDING_1: YES -- codex delayed' "$prod_codex_delay_tmp/codex-vote-output.txt" \
    || { echo "FAIL: production delayed .done path should preserve the codex output after promotion" >&2; exit 1; }
if (( prod_codex_delay_end - prod_codex_delay_start < 1 )); then
    echo "FAIL: production delayed .done path returned before launch-review.sh could promote the delayed codex sentinel" >&2
    exit 1
fi
require_voter_paths_file_nonempty "happy-codex-prod-delay" "$out"

voter1_plugin="$TMP/voter1-plugin"
make_voter1_delayed_done_plugin_root "$voter1_plugin"
voter1_tmp="$TMP/voter1-delayed-done"
mkdir -p "$voter1_tmp"
voter1_start=$(date +%s)
out=$(PATH="$STUB_BIN:$PATH" \
    CLAUDE_PLUGIN_ROOT="$voter1_plugin" \
    LARCH_VOTER1_DONE_DELAY=1 \
    "$voter1_plugin/scripts/dispatch-code-voters.sh" \
        --ballot-file "$BALLOT" \
        --review-tmpdir "$voter1_tmp" \
        --codex-available true \
        --cursor-available true)
voter1_end=$(date +%s)
grep -Fq 'VOTER_1_STATUS=launched' <<< "$out" \
    || { echo "FAIL: delayed voter1 .done wait path should keep voter1 launched" >&2; exit 1; }
grep -Fq 'VOTER_1_PARSE_RATE_STATUS=OK' <<< "$out" \
    || { echo "FAIL: delayed voter1 .done wait path should keep substantive voter1 output parseable" >&2; exit 1; }
[[ -f "$voter1_tmp/claude-vote-output.txt.done" ]] \
    || { echo "FAIL: delayed voter1 .done wait path should publish a done sentinel" >&2; exit 1; }
if (( voter1_end - voter1_start < 1 )); then
    echo "FAIL: delayed voter1 .done wait path returned before the launcher-owned sentinel landed" >&2
    exit 1
fi
require_voter_paths_file_nonempty "happy-voter1-delayed-done" "$out"

voter1_missing_tmp="$TMP/voter1-missing-done"
mkdir -p "$voter1_missing_tmp"
out=$(PATH="$STUB_BIN:$PATH" \
    CLAUDE_PLUGIN_ROOT="$voter1_plugin" \
    LARCH_VOTER_WAIT_TIMEOUT=1 \
    LARCH_VOTER1_DONE_MODE=missing \
    "$voter1_plugin/scripts/dispatch-code-voters.sh" \
        --ballot-file "$BALLOT" \
        --review-tmpdir "$voter1_missing_tmp" \
        --codex-available true \
        --cursor-available true)
grep -Fq 'VOTER_1_STATUS=failed' <<< "$out" \
    || { echo "FAIL: missing voter1 sentinel must fail instead of synthetic-backfill launch success" >&2; exit 1; }
if [[ -e "$voter1_missing_tmp/claude-vote-output.txt.done" ]]; then
    echo "FAIL: missing voter1 sentinel must not be backfilled after timeout" >&2
    exit 1
fi
require_voter_paths_file_nonempty "happy-voter1-missing-done" "$out"

wait_timeout_tmp="$TMP/wait-timeout"
timeout_stderr="$TMP/wait-timeout.stderr"
mkdir -p "$wait_timeout_tmp"
PATH="$STUB_BIN:$PATH" \
    CLAUDE_PLUGIN_ROOT="$wait_plugin" \
    WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05 \
    LARCH_VOTER_WAIT_TIMEOUT=1 \
    LARCH_WAIT_BARRIER_MODE=timeout \
    LARCH_WAIT_BARRIER_VOTER2="$wait_timeout_tmp/codex-vote-output.txt" \
    LARCH_WAIT_BARRIER_VOTER3="$wait_timeout_tmp/cursor-vote-output.txt" \
    "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$wait_timeout_tmp" --codex-available true --cursor-available true \
    > "$TMP/wait-timeout.out" 2> "$timeout_stderr"
out=$(cat "$TMP/wait-timeout.out")
grep -Fq 'VOTER_2_STATUS=failed' <<< "$out" \
    || { echo "FAIL: wait timeout path should fail the missing voter2 output" >&2; exit 1; }
grep -Fq 'VOTER_3_STATUS=failed' <<< "$out" \
    || { echo "FAIL: wait timeout path should fail the missing voter3 output" >&2; exit 1; }
grep -Fq 'DEGRADED_PANEL_WARNING=**⚠ Degraded code-review panel: 1/3 effective judges produced output.**' <<< "$out" \
    || { echo "FAIL: wait timeout path should emit a 1/3 degraded panel warning" >&2; exit 1; }
grep -Fq 'dispatch-code-voters.sh: voter sentinel TIMEOUT 2 codex-vote-output.txt' "$timeout_stderr" \
    || { echo "FAIL: wait timeout path should log voter2 TIMEOUT rows from wait-for-reviewers stdout" >&2; exit 1; }
grep -Fq 'dispatch-code-voters.sh: voter sentinel TIMEOUT 3 cursor-vote-output.txt' "$timeout_stderr" \
    || { echo "FAIL: wait timeout path should log voter3 TIMEOUT rows from wait-for-reviewers stdout" >&2; exit 1; }

wait_nonzero_done_tmp="$TMP/wait-nonzero-done"
mkdir -p "$wait_nonzero_done_tmp"
out=$(PATH="$STUB_BIN:$PATH" \
    CLAUDE_PLUGIN_ROOT="$wait_plugin" \
    WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05 \
    LARCH_VOTER_WAIT_TIMEOUT=2 \
    LARCH_WAIT_BARRIER_MODE=nonzero_done \
    LARCH_WAIT_BARRIER_VOTER2="$wait_nonzero_done_tmp/codex-vote-output.txt" \
    LARCH_WAIT_BARRIER_VOTER3="$wait_nonzero_done_tmp/cursor-vote-output.txt" \
    "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$wait_nonzero_done_tmp" --codex-available true --cursor-available true)
grep -Fq 'VOTER_2_STATUS=failed' <<< "$out" \
    || { echo "FAIL: non-zero voter2 .done exit code must fail the slot even with output bytes present" >&2; exit 1; }
grep -Fq 'VOTER_3_STATUS=failed' <<< "$out" \
    || { echo "FAIL: non-zero voter3 .done exit code must fail the slot even with output bytes present" >&2; exit 1; }
grep -Fq 'DEGRADED_PANEL_WARNING=**⚠ Degraded code-review panel: 1/3 effective judges produced output.**' <<< "$out" \
    || { echo "FAIL: non-zero external voter .done exit codes should degrade the panel to 1/3" >&2; exit 1; }
require_voter_paths_file_nonempty "happy-wait-nonzero-done" "$out"

wait_usage_plugin="$TMP/wait-usage-plugin"
make_wait_usage_error_plugin_root "$wait_usage_plugin"
wait_usage_tmp="$TMP/wait-usage-error"
wait_usage_stderr="$TMP/wait-usage-error.stderr"
mkdir -p "$wait_usage_tmp"
PATH="$STUB_BIN:$PATH" \
    CLAUDE_PLUGIN_ROOT="$wait_usage_plugin" \
    LARCH_WAIT_BARRIER_MODE=immediate \
    LARCH_WAIT_BARRIER_VOTER2="$wait_usage_tmp/codex-vote-output.txt" \
    LARCH_WAIT_BARRIER_VOTER3="$wait_usage_tmp/cursor-vote-output.txt" \
    "$SCRIPT" --ballot-file "$BALLOT" --review-tmpdir "$wait_usage_tmp" --codex-available true --cursor-available true \
    > "$TMP/wait-usage-error.out" 2> "$wait_usage_stderr"
out=$(cat "$TMP/wait-usage-error.out")
grep -Fq 'VOTER_2_STATUS=launched' <<< "$out" \
    || { echo "FAIL: wait usage-error path should still tally existing voter2 output" >&2; exit 1; }
grep -Fq 'VOTER_3_STATUS=launched' <<< "$out" \
    || { echo "FAIL: wait usage-error path should still tally existing voter3 output" >&2; exit 1; }
grep -Fq 'dispatch-code-voters.sh: wait-for-reviewers.sh exited 1 (usage/config error) - proceeding with whatever state exists' "$wait_usage_stderr" \
    || { echo "FAIL: wait usage-error path should log the usage/config diagnostic" >&2; exit 1; }
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
require_voter_paths_file_nonempty "edge-symlink-diff" "$out"

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
require_voter_paths_file_nonempty "edge-big-diff" "$out"

oos_only_ballot="$TMP/oos-only-ballot.md"
cat > "$oos_only_ballot" <<'EOF'
### OOS_1: OOS-only observation
- **Reviewer**: stub
- **Concern**: c1
- **Suggested revision**: r1
EOF
oos_retry_tmp="$TMP/oos-retry"
oos_retry_count="$TMP/oos-retry-count.txt"
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_STUB_MODE=parse_retry_success CLAUDE_STUB_COUNT_FILE="$oos_retry_count" "$SCRIPT" \
    --ballot-file "$oos_only_ballot" \
    --review-tmpdir "$oos_retry_tmp" \
    --codex-available true \
    --cursor-available true)
grep -Fq 'VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE' <<< "$out" \
    || { echo "FAIL: OOS-only ballot should trigger parse-rate retry when voter omits OOS_N" >&2; exit 1; }
grep -Fq 'same ballot ID from the ballot (FINDING_N: or OOS_N:)' "$oos_retry_tmp/claude-vote-prompt-retry.txt" \
    || { echo "FAIL: code voter retry prefix missing dual FINDING/OOS instruction" >&2; exit 1; }
grep -Fq 'Four-axis ratings are required on the same line as every vote.' "$oos_retry_tmp/claude-vote-prompt-retry.txt" \
    || { echo "FAIL: code voter retry prefix missing ratings reminder" >&2; exit 1; }
require_voter_paths_file_nonempty "edge-oos-retry" "$out"

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
    require_voter_paths_file_nonempty "edge-prod-claude" "$out"
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
require_voter_paths_file_nonempty "retry-claude-ok" "$out"

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
require_voter_paths_file_nonempty "retry-claude-fail" "$out"
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
require_voter_paths_file_nonempty "retry-codex-ok" "$out"
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
require_voter_paths_file_nonempty "retry-cursor-ok" "$out"
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

require_voter_paths_file_nonempty "retry-codex-fail" "$out"

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
require_voter_paths_file_nonempty "retry-fallback-claude" "$out"
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
require_voter_paths_file_nonempty "regression1-env-isolation" "$out"

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
require_voter_paths_file_nonempty "regression2-path-guard" "$out"
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
    require_voter_paths_file_nonempty "regression3-prod-codex" "$out"
)
fi  # end section: regressions-r3-codex

echo "PASS: test-dispatch-code-voters.sh"
