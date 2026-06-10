#!/usr/bin/env bash
# Regression harness for launch-claude-drafter.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SUBJECT="$REPO_ROOT/scripts/launch-claude-drafter.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-test-launch-claude-drafter.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

STUB_BIN="$TMPROOT/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/claude" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${LARCH_TEST_CLAUDE_ARGV_LOG:?}"
cat >/dev/null
case "${LARCH_TEST_CLAUDE_MODE:-ok}" in
    invalid-json)
        printf '{not json\n'
        ;;
    is-error)
        printf '{"is_error":true,"result":"bad","usage":{"input_tokens":1}}\n'
        ;;
    empty-result)
        printf '{"result":"","usage":{"input_tokens":1}}\n'
        ;;
    no-summary)
        jq -cn --arg result $'LARCH_PLAN_BEGIN\n## Plan\nBody mentions LARCH_PLAN_BEGIN without sentinel line.\ndiff_lines: 3\nLARCH_PLAN_END\n' '{result:$result,usage:{input_tokens:2,output_tokens:3,cache_read_input_tokens:4,cache_creation_input_tokens:5}}'
        ;;
    bad-delim)
        jq -cn --arg result $'LARCH_PLAN_BEGIN\nbody\nLARCH_PLAN_BEGIN\ndiff_lines: 2\nLARCH_PLAN_END\n' '{result:$result,usage:{input_tokens:1,output_tokens:1}}'
        ;;
    nested-plan-in-summary)
        jq -cn --arg result $'LARCH_SUMMARY_BEGIN\nLARCH_PLAN_BEGIN\nnested plan\ndiff_lines: 2\nLARCH_PLAN_END\nsummary tail\nLARCH_SUMMARY_END\n' '{result:$result,usage:{input_tokens:1,output_tokens:1}}'
        ;;
    missing-diff)
        jq -cn --arg result $'LARCH_PLAN_BEGIN\n## Plan\nNo trailer\nLARCH_PLAN_END\n' '{result:$result,usage:{input_tokens:1,output_tokens:1}}'
        ;;
    *)
        jq -cn --arg result $'LARCH_SUMMARY_BEGIN\nGenerated summary\nLARCH_SUMMARY_END\nLARCH_PLAN_BEGIN\n## Plan\nDetailed body\ndiff_lines: 7\nLARCH_PLAN_END\n' '{result:$result,usage:{input_tokens:2,output_tokens:3,cache_read_input_tokens:4,cache_creation_input_tokens:5}}'
        ;;
esac
STUB
chmod +x "$STUB_BIN/claude"
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
    PATH="$STUB_BIN:$PATH" DESIGN_TMPDIR="$d" IMPLEMENT_TMPDIR="" SESSION_ENV_PATH="" \
        LARCH_QUIET_DISABLE=1 LARCH_TIMING_LEDGER="$TMPROOT/timing.tsv" \
        LARCH_TOKEN_LEDGER="$TMPROOT/tokens.jsonl" LARCH_TEST_CLAUDE_ARGV_LOG="$TMPROOT/claude.argv" "$SUBJECT" \
        --model "${3:-claude-fable-5}" \
        --prompt-file "$d/prompt.txt" \
        --output-file "$out" \
        --timeout 5 \
        --design-tmpdir "$d" \
        --repo-root "$REPO_ROOT" \
        "${@:4}"
}

# Invalid output path can fail before output canonicalization and therefore need not write .dirty-tree.
d0="$TMPROOT/d0"
mkdir -p "$d0"
printf 'prompt\n' > "$d0/prompt.txt"
set +e
PATH="$STUB_BIN:$PATH" LARCH_QUIET_DISABLE=1 IMPLEMENT_TMPDIR="" SESSION_ENV_PATH="" LARCH_TEST_CLAUDE_ARGV_LOG="$TMPROOT/argv-unused" "$SUBJECT" \
    --model claude-fable-5 --prompt-file "$d0/prompt.txt" --output-file "$TMPROOT/missing/out.txt" \
    --timeout 5 --design-tmpdir "$d0" --repo-root "$REPO_ROOT" >/dev/null 2>"$TMPROOT/bad-output.err"
bad_out_rc=$?
set -e
[[ "$bad_out_rc" -eq 2 ]] || fail "invalid output path should exit 2"
[[ ! -e "$TMPROOT/missing/out.txt.dirty-tree" ]] || fail "invalid output path should not create dirty-tree sidecar"

# Successful JSON/result promotion writes plan and summary, keeps status KVs, records argv and token provenance.
d1="$TMPROOT/d1"
mkdir -p "$d1"
printf 'prompt\n' > "$d1/prompt.txt"
out1="$d1/status.txt"
run_drafter "$d1" "$out1" >/dev/null
command grep -Fq 'STATUS=OK' "$out1" || fail "success status missing"
command grep -Fq 'PLAN_WRITTEN=true' "$out1" || fail "plan-written status missing"
command grep -Fq 'SUMMARY_WRITTEN=true' "$out1" || fail "summary-written status missing"
command grep -Fq 'diff_lines: 7' "$d1/plan.txt" || fail "plan.txt not written from result"
command grep -Fq 'Generated summary' "$d1/plan-summary.md" || fail "plan-summary.md not written"
command grep -Fq 'CMD_JSON=' "$out1.meta" || fail "CMD_JSON metadata missing"
command grep -Fq -- '--allowedTools Read,Glob,Grep,LS' "$TMPROOT/claude.argv" || fail "native allowedTools argv mismatch"
argv_contents=$(cat "$TMPROOT/claude.argv")
case "$argv_contents" in
    *--read-tools*|*Write*|*Edit*|*Bash*) fail "mutating or wrapper-only tool leaked into argv" ;;
esac
[[ -f "$out1.done" ]] || fail ".done missing"
[[ -f "$out1.stderr" ]] || fail ".stderr missing"
[[ -f "$out1.dirty-tree" ]] || fail ".dirty-tree missing"
[[ ! -e "$out1.result" && ! -e "$out1.json" ]] || fail "persistent .result/.json sidecar leaked"
command grep -Fq 'raw":"claude_draft' "$TMPROOT/tokens.jsonl" || fail "token row raw=claude_draft missing"

# Valid output path plus invalid prompt containment fails after trap install and writes .dirty-tree.
outside_prompt="$TMPROOT/outside-prompt.txt"
printf 'outside\n' > "$outside_prompt"
out2="$d1/status-invalid-prompt.txt"
set +e
PATH="$STUB_BIN:$PATH" LARCH_QUIET_DISABLE=1 IMPLEMENT_TMPDIR="" SESSION_ENV_PATH="" LARCH_TEST_CLAUDE_ARGV_LOG="$TMPROOT/argv-unused" "$SUBJECT" \
    --model claude-fable-5 --prompt-file "$outside_prompt" --output-file "$out2" \
    --timeout 5 --design-tmpdir "$d1" --repo-root "$REPO_ROOT" >/dev/null 2>"$TMPROOT/invalid-prompt.err"
invalid_prompt_rc=$?
set -e
[[ "$invalid_prompt_rc" -eq 2 ]] || fail "invalid prompt should exit 2"
[[ -f "$out2.dirty-tree" ]] || fail "post-canonicalization failure missing dirty-tree"
command grep -Fq 'MODE=prelaunch' "$out2.dirty-tree" || fail "prelaunch dirty-tree mode missing"

# JSON envelope failures are exit 99, emit fixed diagnostic, and skip token append for that run.
d3="$TMPROOT/d3"
mkdir -p "$d3"
printf 'prompt\n' > "$d3/prompt.txt"
for mode in invalid-json is-error empty-result; do
    before_size=$(wc -c < "$TMPROOT/tokens.jsonl" | tr -d ' ')
    set +e
    LARCH_TEST_CLAUDE_MODE="$mode" run_drafter "$d3" "$d3/status-$mode.txt" >/dev/null 2>"$TMPROOT/$mode.err"
    rc=$?
    set -e
    [[ "$rc" -eq 99 ]] || fail "$mode should exit 99 (got $rc)"
    command grep -Fq 'REASON=CLAUDE_JSON_RESULT_INVALID' "$d3/status-$mode.txt" || fail "$mode missing JSON invalid reason"
    after_size=$(wc -c < "$TMPROOT/tokens.jsonl" | tr -d ' ')
    [[ "$before_size" -eq "$after_size" ]] || fail "$mode should not append token row"
done

# Delimiter and final trailer failures fail closed.
for mode in bad-delim nested-plan-in-summary missing-diff; do
    set +e
    LARCH_TEST_CLAUDE_MODE="$mode" run_drafter "$d3" "$d3/status-$mode.txt" >/dev/null 2>"$TMPROOT/$mode.err"
    rc=$?
    set -e
    [[ "$rc" -eq 99 ]] || fail "$mode should exit 99 (got $rc)"
    command grep -Fq 'REASON=DELIMITER_EXTRACTION_INVALID' "$d3/status-$mode.txt" || fail "$mode missing delimiter invalid reason"
done

# Summary is optional; mentions of delimiter names inside prose are allowed when not exact whole-line sentinels.
d4="$TMPROOT/d4"
mkdir -p "$d4"
printf 'prompt\n' > "$d4/prompt.txt"
LARCH_TEST_CLAUDE_MODE=no-summary run_drafter "$d4" "$d4/status.txt" >/dev/null
command grep -Fq 'SUMMARY_WRITTEN=false' "$d4/status.txt" || fail "summary optional status missing"
[[ ! -e "$d4/plan-summary.md" ]] || fail "summary should not be written when no summary sentinels exist"
command grep -Fq 'Body mentions LARCH_PLAN_BEGIN without sentinel line.' "$d4/plan.txt" || fail "delimiter name in prose was not preserved"

# Baseline delta cases.
d5="$TMPROOT/d5"
mkdir -p "$d5"
printf 'prompt\n' > "$d5/prompt.txt"
printf ' M preexisting.txt\n' > "$d5/baseline.porcelain"
LARCH_TEST_GIT_PORCELAIN=$' M preexisting.txt\n' run_drafter "$d5" "$d5/status-clean.txt" claude-fable-5 --baseline-porcelain "$d5/baseline.porcelain" >/dev/null
command grep -Fq 'STATUS=clean' "$d5/status-clean.txt.dirty-tree" || fail "baseline clean status missing"
command grep -Fq 'MODE=baseline-delta' "$d5/status-clean.txt.dirty-tree" || fail "baseline mode missing"
LARCH_TEST_GIT_PORCELAIN=$' M preexisting.txt\n?? new.txt\n' run_drafter "$d5" "$d5/status-dirty.txt" claude-fable-5 --baseline-porcelain "$d5/baseline.porcelain" >/dev/null
command grep -Fq 'STATUS=dirty' "$d5/status-dirty.txt.dirty-tree" || fail "baseline dirty status missing"
LARCH_TEST_GIT_PORCELAIN=$' M preexisting.txt\n' run_drafter "$d5" "$d5/status-nobase.txt" >/dev/null
command grep -Fq 'STATUS=unknown' "$d5/status-nobase.txt.dirty-tree" || fail "no-baseline dirty should be unknown"
command grep -Fq 'MODE=no-baseline' "$d5/status-nobase.txt.dirty-tree" || fail "no-baseline mode missing"

# Model validation.
set +e
PATH="$STUB_BIN:$PATH" LARCH_QUIET_DISABLE=1 IMPLEMENT_TMPDIR="" SESSION_ENV_PATH="" LARCH_TEST_CLAUDE_ARGV_LOG="$TMPROOT/argv-unused" "$SUBJECT" \
    --model 'bad model' --prompt-file "$d1/prompt.txt" --output-file "$d1/status-bad-model.txt" \
    --timeout 5 --design-tmpdir "$d1" --repo-root "$REPO_ROOT" >/dev/null 2>"$TMPROOT/bad-model.err"
bad_model_rc=$?
set -e
[[ "$bad_model_rc" -eq 2 ]] || fail "bad model should exit 2"

[[ -s "$TMPROOT/timing.tsv" ]] || fail "timing ledger should receive drafter rows"

echo "PASS: test-launch-claude-drafter.sh"
