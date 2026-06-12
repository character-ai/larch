#!/usr/bin/env bash
# Regression harness for launch-codex-drafter.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SUBJECT="$REPO_ROOT/scripts/launch-codex-drafter.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-test-launch-codex-drafter.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

STUB_BIN="$TMPROOT/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/codex" <<'STUB'
#!/usr/bin/env bash
out=""
last=""
for arg in "$@"; do
    if [[ -n "${LARCH_TEST_CODEX_ARGV_LOG:-}" ]]; then
        printf '%s\n' "$arg" >> "$LARCH_TEST_CODEX_ARGV_LOG"
    fi
    if [[ "$last" == "--output-last-message" ]]; then
        out="$arg"
    fi
    last="$arg"
done
if [[ -n "${CODEX_STUB_CONFIG_FILE:-}" && -n "${CODEX_HOME:-}" && -f "$CODEX_HOME/config.toml" ]]; then
    cp "$CODEX_HOME/config.toml" "$CODEX_STUB_CONFIG_FILE"
fi
case "${LARCH_TEST_CODEX_MODE:-ok}" in
    exec-fail)
        printf 'authentication failed sk-larch-drafter-secret-key\n' >&2
        exit 1
        ;;
    empty-output)
        [[ -n "$out" ]] || exit 9
        : > "$out"
        printf '{"msg":{"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        exit 0
        ;;
    bad-delim)
        [[ -n "$out" ]] || exit 9
        printf '%s\n' \
            'LARCH_PLAN_BEGIN' 'body' 'LARCH_PLAN_BEGIN' 'diff_lines: 2' 'LARCH_PLAN_END' > "$out"
        printf '{"msg":{"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        exit 0
        ;;
    nested-plan-in-summary)
        [[ -n "$out" ]] || exit 9
        printf '%s\n' \
            'LARCH_SUMMARY_BEGIN' 'LARCH_PLAN_BEGIN' 'nested plan' 'diff_lines: 2' 'LARCH_PLAN_END' \
            'summary tail' 'LARCH_SUMMARY_END' > "$out"
        printf '{"msg":{"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        exit 0
        ;;
    missing-diff)
        [[ -n "$out" ]] || exit 9
        printf '%s\n' 'LARCH_PLAN_BEGIN' '## Plan' 'No trailer' 'LARCH_PLAN_END' > "$out"
        printf '{"msg":{"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        exit 0
        ;;
    no-summary)
        [[ -n "$out" ]] || exit 9
        printf '%s\n' \
            'LARCH_PLAN_BEGIN' '## Plan' 'Body mentions LARCH_PLAN_BEGIN without sentinel line.' \
            'diff_lines: 3' 'LARCH_PLAN_END' > "$out"
        printf '{"msg":{"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        exit 0
        ;;
    scout-valid)
        [[ -n "$out" ]] || exit 9
        printf '%s\n' \
            'LARCH_PLAN_BEGIN' '## Plan' 'Detailed body' 'diff_lines: 7' 'LARCH_PLAN_END' \
            'LARCH_SCOUT_BEGIN' \
            '{"archetypes":[{"name":"api-contract","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"p"}]}' \
            'LARCH_SCOUT_END' > "$out"
        printf '{"msg":{"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        exit 0
        ;;
    scout-over-cap)
        [[ -n "$out" ]] || exit 9
        printf '%s\n' \
            'LARCH_PLAN_BEGIN' '## Plan' 'Detailed body' 'diff_lines: 7' 'LARCH_PLAN_END' \
            'LARCH_SCOUT_BEGIN' \
            '{"archetypes":[{"name":"api-a","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"p"},{"name":"api-b","focus_area":"architecture","weight":1,"rationale":"r","prompt_body":"p"},{"name":"api-c","focus_area":"security","weight":1,"rationale":"r","prompt_body":"p"},{"name":"api-d","focus_area":"risk-integration","weight":1,"rationale":"r","prompt_body":"p"}]}' \
            'LARCH_SCOUT_END' > "$out"
        printf '{"msg":{"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        exit 0
        ;;
    scout-duplicate)
        [[ -n "$out" ]] || exit 9
        printf '%s\n' \
            'LARCH_PLAN_BEGIN' '## Plan' 'Detailed body' 'diff_lines: 7' 'LARCH_PLAN_END' \
            'LARCH_SCOUT_BEGIN' \
            '{"archetypes":[{"name":"api-a","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"first"},{"name":"api-a","focus_area":"architecture","weight":1,"rationale":"r","prompt_body":"duplicate"},{"name":"api-b","focus_area":"security","weight":1,"rationale":"r","prompt_body":"p"}]}' \
            'LARCH_SCOUT_END' > "$out"
        printf '{"msg":{"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        exit 0
        ;;
    scout-reserved)
        [[ -n "$out" ]] || exit 9
        printf '%s\n' \
            'LARCH_PLAN_BEGIN' '## Plan' 'Detailed body' 'diff_lines: 7' 'LARCH_PLAN_END' \
            'LARCH_SCOUT_BEGIN' \
            '{"archetypes":[{"name":"arch","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"reserved"},{"name":"api-z","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"p"}]}' \
            'LARCH_SCOUT_END' > "$out"
        printf '{"msg":{"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        exit 0
        ;;
    scout-malformed)
        [[ -n "$out" ]] || exit 9
        printf '%s\n' \
            'LARCH_PLAN_BEGIN' '## Plan' 'Detailed body' 'diff_lines: 7' 'LARCH_PLAN_END' \
            'LARCH_SCOUT_BEGIN' '{not json' 'LARCH_SCOUT_END' > "$out"
        printf '{"msg":{"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        exit 0
        ;;
    scout-in-plan)
        [[ -n "$out" ]] || exit 9
        printf '%s\n' \
            'LARCH_PLAN_BEGIN' '## Plan' \
            '{"archetypes":[{"name":"api-contract","focus_area":"correctness","weight":1,"rationale":"r","prompt_body":"literal } brace and { brace inside string"}]}' \
            'diff_lines: 9' 'LARCH_PLAN_END' > "$out"
        printf '{"msg":{"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        exit 0
        ;;
    *)
        [[ -n "$out" ]] || exit 9
        printf '%s\n' \
            'LARCH_SUMMARY_BEGIN' 'Generated summary' 'LARCH_SUMMARY_END' \
            'LARCH_PLAN_BEGIN' '## Plan' 'Detailed body' 'diff_lines: 7' 'LARCH_PLAN_END' > "$out"
        printf '{"msg":{"usage":{"input_tokens":2,"output_tokens":3}}}\n'
        exit 0
        ;;
esac
STUB
chmod +x "$STUB_BIN/codex"
cat > "$STUB_BIN/git" <<'STUB'
#!/usr/bin/env bash
if [[ "$1" == "-C" ]]; then
    shift 2
fi
if [[ "$1" == "status" && "$2" == "--porcelain" ]]; then
    printf '%s' "${LARCH_TEST_GIT_PORCELAIN:-}"
    exit 0
fi
exit 1
STUB
chmod +x "$STUB_BIN/git"

run_drafter() {
    local d="$1" out="$2"
    PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" DESIGN_TMPDIR="$d" \
        IMPLEMENT_TMPDIR="" SESSION_ENV_PATH="" LARCH_QUIET_DISABLE=1 \
        LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0 LARCH_EXTERNAL_AUTH_RETRIES=1 \
        RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
        LARCH_TIMING_LEDGER="$TMPROOT/timing.tsv" \
        LARCH_TEST_CODEX_ARGV_LOG="$TMPROOT/codex.argv" "$SUBJECT" \
        --prompt-file "$d/prompt.txt" \
        --output-file "$out" \
        --timeout 5 \
        --design-tmpdir "$d" \
        --repo-root "$REPO_ROOT" \
        "${@:3}"
}

d0="$TMPROOT/d0"
mkdir -p "$d0"
printf 'prompt\n' > "$d0/prompt.txt"
set +e
PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" LARCH_QUIET_DISABLE=1 \
    IMPLEMENT_TMPDIR="" SESSION_ENV_PATH="" LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0 \
    "$SUBJECT" --prompt-file "$d0/prompt.txt" --output-file "$TMPROOT/missing/out.txt" \
    --timeout 5 --design-tmpdir "$d0" --repo-root "$REPO_ROOT" >/dev/null 2>"$TMPROOT/bad-output.err"
bad_out_rc=$?
set -e
[[ "$bad_out_rc" -eq 2 ]] || fail "invalid output path should exit 2"
[[ ! -e "$TMPROOT/missing/out.txt.dirty-tree" ]] || fail "invalid output path should not create dirty-tree sidecar"

d1="$TMPROOT/d1"
mkdir -p "$d1"
printf 'prompt\n' > "$d1/prompt.txt"
out1="$d1/status.txt"
CODEX_STUB_CONFIG_FILE="$TMPROOT/codex-config.toml" run_drafter "$d1" "$out1" >/dev/null
command grep -Fq 'STATUS=OK' "$out1" || fail "success status missing"
command grep -Fq 'PLAN_WRITTEN=true' "$out1" || fail "plan-written status missing"
command grep -Fq 'SUMMARY_WRITTEN=true' "$out1" || fail "summary-written status missing"
command grep -Fq 'diff_lines: 7' "$d1/plan.txt" || fail "plan.txt not written from codex output"
command grep -Fq 'Generated summary' "$d1/plan-summary.md" || fail "plan-summary.md not written"
command grep -Fxq -- '--sandbox' "$TMPROOT/codex.argv" || fail "read-only sandbox argv missing"
command grep -Fxq -- 'read-only' "$TMPROOT/codex.argv" || fail "read-only sandbox argv missing"
command grep -Fq 'OUTPUT CONTRACT' "$TMPROOT/codex-config.toml" || fail "trusted instructions missing from CODEX_HOME config"
command grep -Fq 'instructions =' "$TMPROOT/codex-config.toml" || fail "instructions field missing from CODEX_HOME config"
[[ -f "$out1.done" ]] || fail ".done missing"
[[ -f "$out1.dirty-tree" ]] || fail ".dirty-tree missing"
[[ ! -e "$out1.stderr-tail" ]] || fail "success should not keep stderr-tail"
command grep -Fxq 'MODEL=gpt-5.5' "$out1.token-record" || fail "success token-record model missing"

outside_prompt="$TMPROOT/outside-prompt.txt"
printf 'outside\n' > "$outside_prompt"
out2="$d1/status-invalid-prompt.txt"
printf 'STALE_TOKEN_RECORD\n' > "$out2.token-record"
set +e
PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" LARCH_QUIET_DISABLE=1 \
    IMPLEMENT_TMPDIR="" SESSION_ENV_PATH="" LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0 \
    "$SUBJECT" --prompt-file "$outside_prompt" --output-file "$out2" \
    --timeout 5 --design-tmpdir "$d1" --repo-root "$REPO_ROOT" >/dev/null 2>"$TMPROOT/invalid-prompt.err"
invalid_prompt_rc=$?
set -e
[[ "$invalid_prompt_rc" -eq 2 ]] || fail "invalid prompt should exit 2"
[[ -f "$out2.dirty-tree" ]] || fail "post-canonicalization failure missing dirty-tree"
command grep -Fq 'MODE=prelaunch' "$out2.dirty-tree" || fail "prelaunch dirty-tree mode missing"
[[ ! -e "$out2.token-record" ]] || fail "prelaunch failure should clear stale token-record"

d3="$TMPROOT/d3"
mkdir -p "$d3"
printf 'prompt\n' > "$d3/prompt.txt"
set +e
LARCH_TEST_CODEX_MODE=exec-fail run_drafter "$d3" "$d3/status-exec-fail.txt" >/dev/null 2>"$TMPROOT/exec-fail.err"
exec_fail_rc=$?
set -e
[[ "$exec_fail_rc" -ne 0 ]] || fail "exec failure should exit non-zero"
command grep -Fq 'REASON=CODEX_EXEC_FAILED' "$d3/status-exec-fail.txt" || fail "exec failure reason missing"
[[ -s "$d3/status-exec-fail.txt.stderr-tail" ]] || fail "exec failure should write stderr-tail"
stderr_tail_lines=$(wc -l < "$d3/status-exec-fail.txt.stderr-tail" | tr -d ' ')
[[ "$stderr_tail_lines" -le 30 ]] || fail "stderr-tail should be bounded"
command grep -Fq '<REDACTED-TOKEN>' "$d3/status-exec-fail.txt.stderr-tail" || fail "stderr-tail should redact secrets"

set +e
LARCH_TEST_CODEX_MODE=empty-output run_drafter "$d3" "$d3/status-empty.txt" >/dev/null 2>"$TMPROOT/empty.err"
empty_rc=$?
set -e
[[ "$empty_rc" -eq 1 ]] || fail "empty output should exit 1"
command grep -Fq 'REASON=CODEX_EMPTY_OUTPUT' "$d3/status-empty.txt" || fail "empty output reason missing"

for mode in bad-delim nested-plan-in-summary missing-diff; do
    set +e
    LARCH_TEST_CODEX_MODE="$mode" run_drafter "$d3" "$d3/status-$mode.txt" >/dev/null 2>"$TMPROOT/$mode.err"
    rc=$?
    set -e
    [[ "$rc" -eq 99 ]] || fail "$mode should exit 99 (got $rc)"
    command grep -Fq 'REASON=DELIMITER_EXTRACTION_INVALID' "$d3/status-$mode.txt" || fail "$mode missing delimiter invalid reason"
done

d4="$TMPROOT/d4"
mkdir -p "$d4"
printf 'prompt\n' > "$d4/prompt.txt"
LARCH_TEST_CODEX_MODE=no-summary run_drafter "$d4" "$d4/status.txt" >/dev/null
command grep -Fq 'SUMMARY_WRITTEN=false' "$d4/status.txt" || fail "summary optional status missing"
[[ ! -e "$d4/plan-summary.md" ]] || fail "summary should not be written when no summary sentinels exist"
command grep -Fq 'Body mentions LARCH_PLAN_BEGIN without sentinel line.' "$d4/plan.txt" || fail "delimiter name in prose was not preserved"

LARCH_TEST_CODEX_MODE=scout-valid run_drafter "$d4" "$d4/status-scout-valid.txt" >/dev/null
command grep -Fq 'SCOUT_WRITTEN=true' "$d4/status-scout-valid.txt" || fail "valid scout status missing"
[[ "$(jq -r '.archetypes | length' "$d4/scout-plan-manifest.json")" == "1" ]] || fail "valid scout manifest not written"

LARCH_TEST_CODEX_MODE=scout-over-cap run_drafter "$d4" "$d4/status-scout-over-cap.txt" >/dev/null
command grep -Fq 'SCOUT_WRITTEN=true' "$d4/status-scout-over-cap.txt" || fail "over-cap scout status missing"
[[ "$(jq -r '.archetypes | length' "$d4/scout-plan-manifest.json")" == "3" ]] || fail "over-cap scout manifest not truncated"
[[ "$(jq -r '.archetypes | map(.name) | join(",")' "$d4/scout-plan-manifest.json")" == "api-a,api-b,api-c" ]] || fail "over-cap scout manifest order changed"

LARCH_TEST_CODEX_MODE=scout-duplicate run_drafter "$d4" "$d4/status-scout-duplicate.txt" >/dev/null
command grep -Fq 'SCOUT_WRITTEN=true' "$d4/status-scout-duplicate.txt" || fail "duplicate scout status missing"
[[ "$(jq -r '.archetypes | map(.name) | join(",")' "$d4/scout-plan-manifest.json")" == "api-a,api-b" ]] || fail "duplicate scout manifest not normalized"

LARCH_TEST_CODEX_MODE=scout-reserved run_drafter "$d4" "$d4/status-scout-reserved.txt" >/dev/null
command grep -Fq 'SCOUT_WRITTEN=true' "$d4/status-scout-reserved.txt" || fail "reserved scout status missing"
[[ "$(jq -r '.archetypes | map(.name) | join(",")' "$d4/scout-plan-manifest.json")" == "api-z" ]] || fail "reserved scout manifest not normalized"

rm -f "$d4/scout-plan-manifest.json"
LARCH_TEST_CODEX_MODE=scout-malformed run_drafter "$d4" "$d4/status-scout-malformed.txt" >/dev/null
command grep -Fq 'SCOUT_WRITTEN=false' "$d4/status-scout-malformed.txt" || fail "malformed scout should not be written"
command grep -Fq 'SCOUT_FAIL_REASON=json_parse' "$d4/status-scout-malformed.txt" || fail "malformed scout fail reason missing"

set +e
LARCH_TEST_CODEX_MODE=scout-in-plan run_drafter "$d4" "$d4/status-scout-in-plan.txt" >/dev/null 2>"$TMPROOT/scout-in-plan.err"
scout_in_plan_rc=$?
set -e
[[ "$scout_in_plan_rc" -eq 99 ]] || fail "standalone scout manifest inside plan should exit 99"
command grep -Fq 'REASON=DELIMITER_EXTRACTION_INVALID' "$d4/status-scout-in-plan.txt" || fail "standalone scout manifest missing delimiter invalid reason"

d5="$TMPROOT/d5"
mkdir -p "$d5"
printf 'prompt\n' > "$d5/prompt.txt"
printf ' M preexisting.txt\n' > "$d5/baseline.porcelain"
LARCH_TEST_GIT_PORCELAIN=$' M preexisting.txt\n' run_drafter "$d5" "$d5/status-clean.txt" --baseline-porcelain "$d5/baseline.porcelain" >/dev/null
command grep -Fq 'STATUS=clean' "$d5/status-clean.txt.dirty-tree" || fail "baseline clean status missing"
command grep -Fq 'MODE=baseline-delta' "$d5/status-clean.txt.dirty-tree" || fail "baseline mode missing"
LARCH_TEST_GIT_PORCELAIN=$' M preexisting.txt\n?? new.txt\n' run_drafter "$d5" "$d5/status-dirty.txt" --baseline-porcelain "$d5/baseline.porcelain" >/dev/null
command grep -Fq 'STATUS=dirty' "$d5/status-dirty.txt.dirty-tree" || fail "baseline dirty status missing"
LARCH_TEST_GIT_PORCELAIN=$' M preexisting.txt\n' run_drafter "$d5" "$d5/status-nobase.txt" >/dev/null
command grep -Fq 'STATUS=unknown' "$d5/status-nobase.txt.dirty-tree" || fail "no-baseline dirty should be unknown"
command grep -Fq 'MODE=no-baseline' "$d5/status-nobase.txt.dirty-tree" || fail "no-baseline mode missing"

[[ -s "$TMPROOT/timing.tsv" ]] || fail "timing ledger should receive drafter rows"

echo "PASS: test-launch-codex-drafter.sh"
