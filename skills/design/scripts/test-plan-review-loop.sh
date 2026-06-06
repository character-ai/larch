#!/usr/bin/env bash
# Offline integration tests for plan-review-loop.sh (PATH-style stubs via LARCH_PLAN_REVIEW_*_SH).

set -euo pipefail
# Fast poll intervals so stub-backed slots don't pay the 10s (run-external-agent)
# or 5s (wait-for-reviewers) sleep cycles.
export RUN_EXTERNAL_AGENT_POLL_INTERVAL="${RUN_EXTERNAL_AGENT_POLL_INTERVAL:-0.05}"
export WAIT_FOR_REVIEWERS_POLL_INTERVAL="${WAIT_FOR_REVIEWERS_POLL_INTERVAL:-0.05}"
export LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
PLR="$ROOT/skills/design/scripts/plan-review-loop.sh"

fail() { printf '%s\n' "$1" >&2; exit 1; }

assert_plan_round_timing_row() {
    local dir="$1" round="$2"
    awk -F '\t' -v r="$round" '$2 == "round" && $4 == "design" && $6 == r { found=1 } END { exit found ? 0 : 1 }' "$dir/timing-ledger.tsv" \
        || fail "missing design round timing row for round $round in $dir"
}

assert_env_has_keys() {
    local path="$1"
    shift
    local key
    for key in "$@"; do
        grep -q "^${key}=" "$path" || fail "missing ${key}= in $path"
    done
}

sorted_file_list() {
    local root="$1"
    (
        cd "$root" || exit 1
        find . -type f | LC_ALL=C sort | sed 's#^\./##'
    )
}

bash -n "$PLR" || fail "bash -n plan-review-loop.sh failed"

set +e
"$PLR" --plan-file "$ROOT/README.md" --codex-present true --cursor-present true 2>/dev/null
rc=$?
set -e
[[ "$rc" == 2 ]] || fail "expected exit 2 when --design-tmpdir missing, got $rc"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-plan-review-loop.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
STUB="$TMP/stub-bin"
mkdir -p "$STUB"

# Hermetic backstop (#3338): prepend minimal external-tool stubs so make lint never blocks on installed-but-unhealthy codex/cursor/claude binaries if a test stub path is missed.
STUB_BIN="$TMP/bin"
mkdir -p "$STUB_BIN"
cat >"$STUB_BIN/codex" <<'STUB_CODEX'
#!/usr/bin/env bash
set -euo pipefail
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then
        output_path="$arg"
    fi
    last="$arg"
done
if [[ -n "$output_path" ]]; then
    printf 'stub codex output\n' >"$output_path"
fi
printf 'stub codex stdout\n'
STUB_CODEX
cat >"$STUB_BIN/cursor" <<'STUB_CURSOR'
#!/usr/bin/env bash
set -euo pipefail
printf '{"result":"stub cursor output","usage":{"inputTokens":0,"outputTokens":0,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
STUB_CURSOR
cat >"$STUB_BIN/claude" <<'STUB_CLAUDE'
#!/usr/bin/env bash
set -euo pipefail
printf 'stub claude stdout\n'
STUB_CLAUDE
chmod +x "$STUB_BIN/codex" "$STUB_BIN/cursor" "$STUB_BIN/claude"
export PATH="$STUB_BIN:$PATH"

set +e
"$PLR" \
    --design-tmpdir "$TMP" \
    --plan-file "$ROOT/README.md" \
    --feature-file "$ROOT/README.md" \
    --codex-present true \
    --cursor-present true \
    --round-num 3 \
    --round-cap 2 >/dev/null 2>&1
rc=$?
set -e
[[ "$rc" == 0 ]] || fail "--round-cap should be inert when --round-num exceeds it, got $rc"

echo "=== removed --convergence-threshold flag rejected ==="
DCT="$TMP/convergence-threshold-removed"
mkdir -p "$DCT"
printf 'plan\n' >"$DCT/plan.txt"
printf 'feat\n' >"$DCT/feature-description.txt"
set +e
ct_out=$("$PLR" \
    --design-tmpdir "$DCT" \
    --plan-file "$DCT/plan.txt" \
    --feature-file "$DCT/feature-description.txt" \
    --codex-present true \
    --cursor-present true \
    --convergence-threshold 3 2>&1)
ct_rc=$?
set -e
[[ "$ct_rc" -eq 2 ]] || fail "expected exit 2 for removed --convergence-threshold, got $ct_rc"
printf '%s\n' "$ct_out" | grep -Fq 'unknown option' || fail "removed --convergence-threshold should fail via unknown option path"

write_scout() {
    cat >"$STUB/scout-plan-archetypes-wrapper.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${PLAN_REVIEW_SCOUT_ARGV_LOG:-}" ]]; then
    printf '%q ' "$@" >>"$PLAN_REVIEW_SCOUT_ARGV_LOG"
    printf '\n' >>"$PLAN_REVIEW_SCOUT_ARGV_LOG"
fi
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) out="${2:?}"; shift 2 ;;
        --plan-file|--description-file|--max-archetypes|--session-env-path|--codex-present|--cursor-present) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$out" ]] || exit 2
printf '%s\n' '{"archetypes":[]}' >"$out"
EOS
    chmod +x "$STUB/scout-plan-archetypes-wrapper.sh"
}

write_dispatch_one_slot() {
    cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
PLAN_FILE=""
FEATURE_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?}"; shift 2 ;;
        --codex-present|--cursor-present|--timeout) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" && -n "$PLAN_FILE" && -n "$FEATURE_FILE" ]] || exit 2
OUT="$DESIGN_TMPDIR/cursor-plan-arch-output.txt"
PROMPT="$DESIGN_TMPDIR/render-plan-cursor-arch.prompt"
printf '%s\n' '{"slot":"cursor-plan-arch","tool":"cursor","output":"'"$OUT"'","prompt_file":"'"$PROMPT"'"}' >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
: >"$OUT"
: >"$PROMPT"
cp "$FEATURE_FILE" "$DESIGN_TMPDIR/feature-file-seen.txt"
printf '%s\n' "$FEATURE_FILE" >"$DESIGN_TMPDIR/feature-file-path.txt"
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
printf '%s\n' "$OUT" >"$PATHS"
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nPHASE2_RELAUNCH_COUNT=0\nCOMBINED_FALLBACK_COUNT=0\nSTATIC_DISPATCH_OK=true\nPANEL_PATHS_FILE=%s\nALL_OUTPUT_FILES_PATH=%s\n' "$PATHS" "$PATHS"
EOS
    chmod +x "$STUB/dispatch-plan-review-panel.sh"
}

write_dispatch_combined_threshold() {
    cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --plan-file|--feature-file|--codex-present|--cursor-present|--timeout) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
OUT="$DESIGN_TMPDIR/cursor-plan-arch-output.txt"
PROMPT="$DESIGN_TMPDIR/render-plan-cursor-arch.prompt"
printf '%s\n' '{"slot":"cursor-plan-arch","tool":"cursor","output":"'"$OUT"'","prompt_file":"'"$PROMPT"'"}' >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
: >"$OUT"
: >"$PROMPT"
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
printf '%s\n' "$OUT" >"$PATHS"
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nPHASE2_RELAUNCH_COUNT=0\nCOMBINED_FALLBACK_COUNT=1\nSTATIC_DISPATCH_OK=true\nPANEL_PATHS_FILE=%s\nALL_OUTPUT_FILES_PATH=%s\n' "$PATHS" "$PATHS"
EOS
    chmod +x "$STUB/dispatch-plan-review-panel.sh"
}

write_dispatch_round2_degraded() {
    cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --plan-file|--feature-file|--codex-present|--cursor-present|--timeout) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
state_file="$DESIGN_TMPDIR/.dispatch-round-count"
round=1
if [[ -f "$state_file" ]]; then
    round=$(( $(cat "$state_file") + 1 ))
fi
printf '%s\n' "$round" >"$state_file"
OUT="$DESIGN_TMPDIR/cursor-plan-arch-output.txt"
PROMPT="$DESIGN_TMPDIR/render-plan-cursor-arch.prompt"
printf '%s\n' '{"slot":"cursor-plan-arch","tool":"cursor","output":"'"$OUT"'","prompt_file":"'"$PROMPT"'"}' >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
: >"$OUT"
: >"$PROMPT"
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
printf '%s\n' "$OUT" >"$PATHS"
combined=0
if [[ "$round" == "2" ]]; then
    combined=1
fi
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nPHASE2_RELAUNCH_COUNT=0\nCOMBINED_FALLBACK_COUNT=%s\nSTATIC_DISPATCH_OK=true\nPANEL_PATHS_FILE=%s\nALL_OUTPUT_FILES_PATH=%s\n' "$combined" "$PATHS" "$PATHS"
EOS
    chmod +x "$STUB/dispatch-plan-review-panel.sh"
}

write_collect_important_round2() {
    cat >"$STUB/collect-agent-results.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
paths=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --paths-file) paths="${2:?}"; shift 2 ;;
        --timeout) shift 2 ;;
        --substantive-validation|--validation-mode|--structured-reviewer-validation) shift 1 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$paths" && -f "$paths" ]] || exit 1
state_file="$(dirname "$paths")/.collect-round-count"
round=1
if [[ -f "$state_file" ]]; then
    round=$(( $(cat "$state_file") + 1 ))
fi
printf '%s\n' "$round" >"$state_file"
while IFS= read -r p || [[ -n "$p" ]]; do
    [[ -z "$p" ]] && continue
    tsv="${p}.tsv"
    {
        printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix"
        if [[ "$round" == "2" ]]; then
            printf '%s\n' "in_scope	important	correctness	src/a	Important streak reset finding	scenario	fix"
        else
            printf '%s\n' "in_scope	nit	correctness	src/a	Nit streak finding	scenario	fix"
        fi
    } >"$tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
    chmod +x "$STUB/collect-agent-results.sh"
}

write_dispatch_round1_degraded_then_ok() {
    cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --plan-file|--feature-file|--codex-present|--cursor-present|--timeout) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
state_file="$DESIGN_TMPDIR/.dispatch-round-count"
round=1
if [[ -f "$state_file" ]]; then
    round=$(( $(cat "$state_file") + 1 ))
fi
printf '%s\n' "$round" >"$state_file"
OUT="$DESIGN_TMPDIR/cursor-plan-arch-output.txt"
PROMPT="$DESIGN_TMPDIR/render-plan-cursor-arch.prompt"
printf '%s\n' '{"slot":"cursor-plan-arch","tool":"cursor","output":"'"$OUT"'","prompt_file":"'"$PROMPT"'"}' >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
: >"$OUT"
: >"$PROMPT"
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
printf '%s\n' "$OUT" >"$PATHS"
combined=0
if [[ "$round" == "1" ]]; then
    combined=1
fi
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nPHASE2_RELAUNCH_COUNT=0\nCOMBINED_FALLBACK_COUNT=%s\nSTATIC_DISPATCH_OK=true\nPANEL_PATHS_FILE=%s\nALL_OUTPUT_FILES_PATH=%s\n' "$combined" "$PATHS" "$PATHS"
EOS
    chmod +x "$STUB/dispatch-plan-review-panel.sh"
}

write_dispatch_three_slots() {
    cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
PLAN_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?}"; shift 2 ;;
        --feature-file|--codex-present|--cursor-present|--timeout) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" && -n "$PLAN_FILE" ]] || exit 2
OUT1="$DESIGN_TMPDIR/rv1.txt"
OUT2="$DESIGN_TMPDIR/rv2.txt"
OUT3="$DESIGN_TMPDIR/rv3.txt"
PROMPT1="$DESIGN_TMPDIR/p1.prompt"
PROMPT2="$DESIGN_TMPDIR/p2.prompt"
PROMPT3="$DESIGN_TMPDIR/p3.prompt"
: >"$OUT1"
: >"$OUT2"
: >"$OUT3"
: >"$PROMPT1"
: >"$PROMPT2"
: >"$PROMPT3"
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
{
    printf '%s\n' '{"slot":"cursor-plan-arch","tool":"cursor","output":"'"$OUT1"'","prompt_file":"'"$PROMPT1"'"}'
    printf '%s\n' '{"slot":"cursor-plan-edge","tool":"cursor","output":"'"$OUT2"'","prompt_file":"'"$PROMPT2"'"}'
    printf '%s\n' '{"slot":"cursor-plan-innov","tool":"cursor","output":"'"$OUT3"'","prompt_file":"'"$PROMPT3"'"}'
} >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
printf '%s\n' "$OUT1" "$OUT2" "$OUT3" >"$PATHS"
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nPHASE2_RELAUNCH_COUNT=0\nCOMBINED_FALLBACK_COUNT=0\nSTATIC_DISPATCH_OK=true\nPANEL_PATHS_FILE=%s\nALL_OUTPUT_FILES_PATH=%s\n' "$PATHS" "$PATHS"
EOS
    chmod +x "$STUB/dispatch-plan-review-panel.sh"
}

write_dispatch_fail() {
    cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
printf 'DISPATCH_OK=false\nFALLBACK_COUNT=0\nPHASE2_RELAUNCH_COUNT=0\nCOMBINED_FALLBACK_COUNT=0\nSTATIC_DISPATCH_OK=false\n'
EOS
    chmod +x "$STUB/dispatch-plan-review-panel.sh"
}

write_dispatch_empty_paths_ok() {
    cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --plan-file|--feature-file|--codex-present|--cursor-present|--timeout) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
: >"$PATHS"
: >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nPHASE2_RELAUNCH_COUNT=0\nCOMBINED_FALLBACK_COUNT=0\nSTATIC_DISPATCH_OK=false\nDEGRADED_ROUND=true\nALL_SLOTS_DROPPED=true\nPANEL_PATHS_FILE=%s\nALL_OUTPUT_FILES_PATH=%s\n' "$PATHS" "$PATHS"
EOS
    chmod +x "$STUB/dispatch-plan-review-panel.sh"
}

write_dispatch_degraded() {
    write_dispatch_combined_threshold
}

write_dispatch_no_paths_degraded() {
    write_dispatch_empty_paths_ok
}

write_dispatch_dropped_slots() {
    # #3392: panel reports all slots dropped under --no-fallback and forwards a
    # DROPPED_SLOTS_FILE sidecar with per-slot reasons + snippets.
    cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --plan-file|--feature-file|--codex-present|--cursor-present|--timeout) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
: >"$PATHS"
: >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
DROPS="$DESIGN_TMPDIR/plan-review-slots.ndjson.output-files.dropped-slots"
printf 'cursor-plan-arch\tcursor\tformat-gate-miss\tReviewing the plan against the repo: it looks solid overall.\n' >"$DROPS"
printf 'codex-plan-edge\tcodex\tcollector-failure\tSTATUS=CODEX_USAGE_LIMIT \n' >>"$DROPS"
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nPHASE2_RELAUNCH_COUNT=0\nCOMBINED_FALLBACK_COUNT=0\nSTATIC_DISPATCH_OK=false\nDEGRADED_ROUND=true\nALL_SLOTS_DROPPED=true\nDROPPED_SLOTS_FILE=%s\nPANEL_PATHS_FILE=%s\nALL_OUTPUT_FILES_PATH=%s\n' "$DROPS" "$PATHS" "$PATHS"
EOS
    chmod +x "$STUB/dispatch-plan-review-panel.sh"
}

write_dispatch_both_absent_generic() {
    cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
CODEX_PRESENT=""
CURSOR_PRESENT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --codex-present) CODEX_PRESENT="${2:?}"; shift 2 ;;
        --cursor-present) CURSOR_PRESENT="${2:?}"; shift 2 ;;
        --plan-file|--feature-file|--timeout) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
[[ "$CODEX_PRESENT" == "false" && "$CURSOR_PRESENT" == "false" ]] || exit 3
OUT="$DESIGN_TMPDIR/claude-plan-generic-output.txt"
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
: >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
printf 'schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix\n' >"${OUT}.tsv"
printf '{"no_issues_found":true}\n' >"$OUT"
printf '0\n' >"${OUT}.done"
printf '%s\n' "$OUT" >"$PATHS"
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nPHASE2_RELAUNCH_COUNT=0\nCOMBINED_FALLBACK_COUNT=0\nSTATIC_DISPATCH_OK=true\nDEGRADED_ROUND=false\nPANEL_PATHS_FILE=%s\nALL_OUTPUT_FILES_PATH=%s\n' "$PATHS" "$PATHS"
EOS
    chmod +x "$STUB/dispatch-plan-review-panel.sh"
}

write_dispatch_cursor_only() {
    cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --plan-file|--feature-file|--codex-present|--cursor-present|--timeout) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
OUT="$DESIGN_TMPDIR/cursor-plan-arch-output.txt"
PROMPT="$DESIGN_TMPDIR/render-plan-cursor-arch.prompt"
printf '%s\n' '{"slot":"cursor-plan-arch","tool":"cursor","output":"'"$OUT"'","prompt_file":"'"$PROMPT"'"}' >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
: >"$OUT"
: >"$PROMPT"
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
printf '%s\n' "$OUT" >"$PATHS"
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nPHASE2_RELAUNCH_COUNT=0\nCOMBINED_FALLBACK_COUNT=0\nSTATIC_DISPATCH_OK=true\nPANEL_PATHS_FILE=%s\nALL_OUTPUT_FILES_PATH=%s\n' "$PATHS" "$PATHS"
EOS
    chmod +x "$STUB/dispatch-plan-review-panel.sh"
}

write_collect_no_sentinel_timeout() {
    cat >"$STUB/collect-agent-results.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
paths=""
timeout=60
while [[ $# -gt 0 ]]; do
    case "$1" in
        --paths-file) paths="${2:?}"; shift 2 ;;
        --timeout) timeout="${2:?}"; shift 2 ;;
        --substantive-validation|--validation-mode|--structured-reviewer-validation) shift 1 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$paths" && -f "$paths" ]] || exit 0
while IFS= read -r p || [[ -n "$p" ]]; do
    [[ -n "$p" ]] || continue
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\nFAILURE_REASON=\n\n' "$p"
done <"$paths"
EOS
    chmod +x "$STUB/collect-agent-results.sh"
}

write_collect_one_nit() {
    write_collect one_nit
}

write_collect_no_findings() {
    write_collect empty
}

write_collect_important() {
    write_collect one
}

write_collect_important_with_oos() {
    write_collect_with_oos_votes
}

write_collect_empty_fail() {
    cat >"$STUB/collect-agent-results.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
exit 1
EOS
    chmod +x "$STUB/collect-agent-results.sh"
}

write_collect_failing_tail() {
    cat >"$STUB/collect-agent-results.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' '--- failed agent stderr tail ---' >&2
printf '%s\n' 'LARCH_TEST_STDERR_TAIL_MARKER' >&2
paths=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --paths-file) paths="${2:?}"; shift 2 ;;
        --timeout) shift 2 ;;
        --substantive-validation|--validation-mode|--structured-reviewer-validation) shift 1 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$paths" && -f "$paths" ]] || exit 1
while IFS= read -r p || [[ -n "$p" ]]; do
    [[ -z "$p" ]] && continue
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=FAIL\nEXIT_CODE=1\n\n' "$p"
done <"$paths"
exit 1
EOS
    chmod +x "$STUB/collect-agent-results.sh"
}

write_collect() {
    local mode="${1:?}"
    cat >"$STUB/collect-agent-results.sh" <<EOS
#!/usr/bin/env bash
set -euo pipefail
paths=""
while [[ \$# -gt 0 ]]; do
    case "\$1" in
        --paths-file) paths="\${2:?}"; shift 2 ;;
        --timeout) shift 2 ;;
        --substantive-validation|--validation-mode|--structured-reviewer-validation) shift 1 ;;
        *) shift 1 ;;
    esac
done
[[ -n "\$paths" && -f "\$paths" ]] || exit 1
idx=0
while IFS= read -r p || [[ -n "\$p" ]]; do
    [[ -z "\$p" ]] && continue
    tsv="\${p}.tsv"
    {
        printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix"
EOS
    if [[ "$mode" == "empty" ]]; then
        cat >>"$STUB/collect-agent-results.sh" <<'EOS'
    } >"$tsv"
EOS
    elif [[ "$mode" == "no_issues_sentinel" ]]; then
        cat >>"$STUB/collect-agent-results.sh" <<'EOS'
    } >"$tsv"
    printf '{"no_issues_found": true}\n' >"$p"
EOS
    elif [[ "$mode" == "one_nit" ]]; then
        cat >>"$STUB/collect-agent-results.sh" <<'EOS'
        printf '%s\n' "in_scope	nit	correctness	src/a	Nit streak finding	scenario	fix"
    } >"$tsv"
EOS
    elif [[ "$mode" == "above_threshold" ]]; then
        cat >>"$STUB/collect-agent-results.sh" <<'EOS'
        printf '%s\n' "in_scope	nit	correctness	src/a	Above threshold finding A	scenario	fix"
        printf '%s\n' "in_scope	nit	correctness	src/b	Above threshold finding B	scenario	fix"
        printf '%s\n' "in_scope	nit	correctness	src/c	Above threshold finding C	scenario	fix"
        printf '%s\n' "in_scope	nit	correctness	src/d	Above threshold finding D	scenario	fix"
    } >"$tsv"
EOS
    elif [[ "$mode" == "five_latent" ]]; then
        cat >>"$STUB/collect-agent-results.sh" <<'EOS'
        printf '%s\n' "in_scope	latent	correctness	src/f1	Five latent one	scenario	fix"
        printf '%s\n' "in_scope	latent	correctness	src/f2	Five latent two	scenario	fix"
        printf '%s\n' "in_scope	latent	correctness	src/f3	Five latent three	scenario	fix"
        printf '%s\n' "in_scope	latent	correctness	src/f4	Five latent four	scenario	fix"
        printf '%s\n' "in_scope	latent	correctness	src/f5	Five latent five	scenario	fix"
    } >"$tsv"
EOS
    elif [[ "$mode" == "six_latent" ]]; then
        cat >>"$STUB/collect-agent-results.sh" <<'EOS'
        printf '%s\n' "in_scope	latent	correctness	src/s1	Six latent one	scenario	fix"
        printf '%s\n' "in_scope	latent	correctness	src/s2	Six latent two	scenario	fix"
        printf '%s\n' "in_scope	latent	correctness	src/s3	Six latent three	scenario	fix"
        printf '%s\n' "in_scope	latent	correctness	src/s4	Six latent four	scenario	fix"
        printf '%s\n' "in_scope	latent	correctness	src/s5	Six latent five	scenario	fix"
        printf '%s\n' "in_scope	latent	correctness	src/s6	Six latent six	scenario	fix"
    } >"$tsv"
EOS
    elif [[ "$mode" == "many_nits_three_latent" ]]; then
        cat >>"$STUB/collect-agent-results.sh" <<'EOS'
        printf '%s\n' "in_scope	nit	correctness	src/n1	Nit bulk one	scenario	fix"
        printf '%s\n' "in_scope	nit	correctness	src/n2	Nit bulk two	scenario	fix"
        printf '%s\n' "in_scope	nit	correctness	src/n3	Nit bulk three	scenario	fix"
        printf '%s\n' "in_scope	nit	correctness	src/n4	Nit bulk four	scenario	fix"
        printf '%s\n' "in_scope	nit	correctness	src/n5	Nit bulk five	scenario	fix"
        printf '%s\n' "in_scope	nit	correctness	src/n6	Nit bulk six	scenario	fix"
        printf '%s\n' "in_scope	nit	correctness	src/n7	Nit bulk seven	scenario	fix"
        printf '%s\n' "in_scope	nit	correctness	src/n8	Nit bulk eight	scenario	fix"
        printf '%s\n' "in_scope	nit	correctness	src/n9	Nit bulk nine	scenario	fix"
        printf '%s\n' "in_scope	nit	correctness	src/n10	Nit bulk ten	scenario	fix"
        printf '%s\n' "in_scope	latent	correctness	src/l1	Latent one	scenario	fix"
        printf '%s\n' "in_scope	latent	correctness	src/l2	Latent two	scenario	fix"
        printf '%s\n' "in_scope	latent	correctness	src/l3	Latent three	scenario	fix"
    } >"$tsv"
EOS
    elif [[ "$mode" == "three_distinct" ]]; then
        cat >>"$STUB/collect-agent-results.sh" <<'EOS'
    idx=$((idx + 1))
        case "$idx" in
            1)
                printf '%s\n' "in_scope	important	correctness	src/a	Alpha zqf9m planreview distinct finding	scenario one	fix one"
                printf '%s\n' "out_of_scope	important	correctness	src/oos1	Beta kjp2x planreview distinct oos	scenario oos	fix oos"
                ;;
            2)
                printf '%s\n' "in_scope	important	correctness	src/b	Gamma nmr7w planreview distinct finding	scenario two	fix two"
                printf '%s\n' "out_of_scope	important	correctness	src/oos2	Delta hxp4q planreview distinct oos	scenario oos2	fix oos2"
                ;;
            3)
                printf '%s\n' "in_scope	important	correctness	src/c	Epsilon wvt8r planreview distinct finding	scenario three	fix three"
                printf '%s\n' "out_of_scope	important	correctness	src/oos3	Zeta mlb3s planreview distinct oos	scenario oos3	fix oos3"
                ;;
            *) printf '%s\n' "in_scope	important	correctness	src/x	unexpected row	scen	fix" ;;
        esac
    } >"$tsv"
EOS
    else
        cat >>"$STUB/collect-agent-results.sh" <<'EOS'
        printf '%s\n' "in_scope	important	correctness	src/a	Alpha concern text goes here	scenario one	fix one"
    } >"$tsv"
EOS
    fi
    cat >>"$STUB/collect-agent-results.sh" <<'EOS'
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
    chmod +x "$STUB/collect-agent-results.sh"
}

write_collect_with_oos_votes() {
    cat >"$STUB/collect-agent-results.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
paths=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --paths-file) paths="${2:?}"; shift 2 ;;
        --timeout) shift 2 ;;
        --substantive-validation|--validation-mode|--structured-reviewer-validation) shift 1 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$paths" && -f "$paths" ]] || exit 1
while IFS= read -r p || [[ -n "$p" ]]; do
    [[ -z "$p" ]] && continue
    tsv="${p}.tsv"
    {
        printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix"
        printf '%s\n' "in_scope	important	correctness	src/a	Accepted finding	scenario	fix"
        printf '%s\n' "out_of_scope	important	correctness	src/oos1	accepted OOS problem	scenario accepted	fix accepted"
        printf '%s\n' "out_of_scope	important	correctness	src/oos2	rejected OOS problem	scenario rejected	fix rejected"
    } >"$tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
    chmod +x "$STUB/collect-agent-results.sh"
}

write_collect_distinct_oos_per_round() {
    cat >"$STUB/collect-agent-results.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
paths=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --paths-file) paths="${2:?}"; shift 2 ;;
        --timeout) shift 2 ;;
        --substantive-validation|--validation-mode|--structured-reviewer-validation) shift 1 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$paths" && -f "$paths" ]] || exit 1
state_file="$(dirname "$paths")/.collect-round-count"
round=1
if [[ -f "$state_file" ]]; then
    round=$(( $(cat "$state_file") + 1 ))
fi
printf '%s\n' "$round" >"$state_file"
while IFS= read -r p || [[ -n "$p" ]]; do
    [[ -z "$p" ]] && continue
    tsv="${p}.tsv"
    {
        printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix"
        printf '%s\n' "in_scope	important	correctness	src/a	Round ${round} finding	scenario ${round}	fix ${round}"
        printf '%s\n' "out_of_scope	important	correctness	src/oos${round}	Round ${round} accepted OOS	scenario ${round}	fix ${round}"
    } >"$tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
    chmod +x "$STUB/collect-agent-results.sh"
}

write_voters_yes_n() {
    local n="${1:?}"
    cat >"$STUB/dispatch-plan-voters.sh" <<EOS
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ \$# -gt 0 ]]; do
    case "\$1" in
        --design-tmpdir) DESIGN_TMPDIR="\${2:?}"; shift 2 ;;
        --ballot-file|--codex-available|--cursor-available|--session-env-path) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "\$DESIGN_TMPDIR" ]] || exit 2
v1="\$DESIGN_TMPDIR/vstub1.txt"
v2="\$DESIGN_TMPDIR/vstub2.txt"
v3="\$DESIGN_TMPDIR/vstub3.txt"
vp="\$DESIGN_TMPDIR/voter-paths.list"
_vote_body=""
for (( _vi=1; _vi<=${n}; _vi++ )); do
    _vote_body+="\$(printf 'FINDING_%s: YES\\n' "\$_vi")"
done
for f in "\$v1" "\$v2" "\$v3"; do
    printf '%s' "\$_vote_body" >"\$f"
done
printf '%s\n' "\$v1" "\$v2" "\$v3" >"\$vp"
printf 'DISPATCH_OK=true\nVOTER_PATHS_FILE=%s\nVOTER_1_PARSE_RATE_STATUS=ok\n' "\$vp"
printf 'VOTER_1_PATH=%s\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\n' "\$v1"
printf 'VOTER_2_PATH=%s\nVOTER_2_TOOL=codex\nVOTER_2_STATUS=launched\n' "\$v2"
printf 'VOTER_3_PATH=%s\nVOTER_3_TOOL=cursor\nVOTER_3_STATUS=launched\n' "\$v3"
EOS
    chmod +x "$STUB/dispatch-plan-voters.sh"
}

write_voters_three() {
    cat >"$STUB/dispatch-plan-voters.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
if [[ -n "${PLAN_REVIEW_VOTER_ARGV_LOG:-}" ]]; then
    printf '%q ' "$@" >>"$PLAN_REVIEW_VOTER_ARGV_LOG"
    printf '\n' >>"$PLAN_REVIEW_VOTER_ARGV_LOG"
fi
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --ballot-file|--codex-available|--cursor-available|--session-env-path|--scope-anchor-file) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
v1="$DESIGN_TMPDIR/vstub1.txt"
v2="$DESIGN_TMPDIR/vstub2.txt"
v3="$DESIGN_TMPDIR/vstub3.txt"
vp="$DESIGN_TMPDIR/voter-paths.list"
for f in "$v1" "$v2" "$v3"; do
    cat >"$f" <<'INNER'
FINDING_1: YES
OOS_1: YES
OOS_2: NO
INNER
done
printf '%s\n' "$v1" "$v2" "$v3" >"$vp"
printf 'DISPATCH_OK=true\nVOTER_PATHS_FILE=%s\nVOTER_1_PARSE_RATE_STATUS=ok\n' "$vp"
printf 'VOTER_1_PATH=%s\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\n' "$v1"
printf 'VOTER_2_PATH=%s\nVOTER_2_TOOL=codex\nVOTER_2_STATUS=launched\n' "$v2"
printf 'VOTER_3_PATH=%s\nVOTER_3_TOOL=cursor\nVOTER_3_STATUS=launched\n' "$v3"
EOS
    chmod +x "$STUB/dispatch-plan-voters.sh"
}

write_voters_with_oos_split() {
    cat >"$STUB/dispatch-plan-voters.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --ballot-file|--codex-available|--cursor-available|--session-env-path) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
v1="$DESIGN_TMPDIR/vstub1.txt"
v2="$DESIGN_TMPDIR/vstub2.txt"
v3="$DESIGN_TMPDIR/vstub3.txt"
vp="$DESIGN_TMPDIR/voter-paths.list"
_vote_body=$'FINDING_1: YES\nOOS_1: YES\nOOS_2: NO\n'
for f in "$v1" "$v2" "$v3"; do
    printf '%s' "$_vote_body" >"$f"
done
printf '%s\n' "$v1" "$v2" "$v3" >"$vp"
printf 'DISPATCH_OK=true\nVOTER_PATHS_FILE=%s\nVOTER_1_PARSE_RATE_STATUS=ok\n' "$vp"
printf 'VOTER_1_PATH=%s\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\n' "$v1"
printf 'VOTER_2_PATH=%s\nVOTER_2_TOOL=codex\nVOTER_2_STATUS=launched\n' "$v2"
printf 'VOTER_3_PATH=%s\nVOTER_3_TOOL=cursor\nVOTER_3_STATUS=launched\n' "$v3"
EOS
    chmod +x "$STUB/dispatch-plan-voters.sh"
}

write_tally_main_agent_stub() {
    cat >"$STUB/tally-plan-review.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --ballot-file|--findings-classification-out|--voter) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
cat >"$DESIGN_TMPDIR/oos-accepted-design.md" <<'INNER'
### OOS_1:
- **Description**: main-agent accepted OOS. Scenario: branch coverage
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: src/oos
- **Phase**: design

INNER
printf 'TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nVOTING_TALLY_FILE=%s\n' "$DESIGN_TMPDIR/voting-tally.md"
EOS
    chmod +x "$STUB/tally-plan-review.sh"
}

write_tally_main_agent() {
    write_tally_main_agent_stub
    export LARCH_PLAN_REVIEW_TALLY_SH="$STUB/tally-plan-review.sh"
}

write_tally_error() {
    cat >"$STUB/tally-plan-review.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --ballot-file|--findings-classification-out|--voter) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
printf 'TALLY_PLAN_REVIEW_STATUS=tally-error\nVOTING_TALLY_FILE=%s\n' "$DESIGN_TMPDIR/voting-tally.md"
exit 2
EOS
    chmod +x "$STUB/tally-plan-review.sh"
    export LARCH_PLAN_REVIEW_TALLY_SH="$STUB/tally-plan-review.sh"
}

write_voters_slot2_failed() {
    cat >"$STUB/dispatch-plan-voters.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --ballot-file|--codex-available|--cursor-available|--session-env-path) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
v1="$DESIGN_TMPDIR/claude-vote-output.txt"
v3="$DESIGN_TMPDIR/cursor-vote-output.txt"
vp="$DESIGN_TMPDIR/voter-paths.list"
for f in "$v1" "$v3"; do
    cat >"$f" <<'INNER'
FINDING_1: YES
INNER
done
printf '%s\n' "$v1" "$v3" >"$vp"
printf 'DISPATCH_OK=true\nVOTER_PATHS_FILE=%s\nVOTER_1_PARSE_RATE_STATUS=ok\n' "$vp"
printf 'VOTER_1_PATH=%s\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\n' "$v1"
printf 'VOTER_2_PATH=%s\nVOTER_2_TOOL=codex\nVOTER_2_STATUS=failed\n' "$DESIGN_TMPDIR/codex-vote-output.txt"
printf 'VOTER_3_PATH=%s\nVOTER_3_TOOL=cursor\nVOTER_3_STATUS=launched\n' "$v3"
EOS
    chmod +x "$STUB/dispatch-plan-voters.sh"
}

# Plan ballot after dedup: three FINDING_* and three OOS_* blocks (tally needs one line per id per voter).
write_voters_plan_six() {
    cat >"$STUB/dispatch-plan-voters.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --ballot-file|--codex-available|--cursor-available|--session-env-path) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
v1="$DESIGN_TMPDIR/vstub1.txt"
v2="$DESIGN_TMPDIR/vstub2.txt"
v3="$DESIGN_TMPDIR/vstub3.txt"
vp="$DESIGN_TMPDIR/voter-paths.list"
_vote_body=$'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\nOOS_1: YES\nOOS_2: YES\nOOS_3: YES\n'
for f in "$v1" "$v2" "$v3"; do
    printf '%s' "$_vote_body" >"$f"
done
printf '%s\n' "$v1" "$v2" "$v3" >"$vp"
printf 'DISPATCH_OK=true\nVOTER_PATHS_FILE=%s\nVOTER_1_PARSE_RATE_STATUS=ok\n' "$vp"
printf 'VOTER_1_PATH=%s\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\n' "$v1"
printf 'VOTER_2_PATH=%s\nVOTER_2_TOOL=codex\nVOTER_2_STATUS=launched\n' "$v2"
printf 'VOTER_3_PATH=%s\nVOTER_3_TOOL=cursor\nVOTER_3_STATUS=launched\n' "$v3"
EOS
    chmod +x "$STUB/dispatch-plan-voters.sh"
}

write_tally_fail() {
    cat >"$STUB/tally-plan-review.sh" <<'EOS'
#!/usr/bin/env bash
echo "tally stub failure" >&2
exit 2
EOS
    chmod +x "$STUB/tally-plan-review.sh"
}

run_loop() {
    local d="$1"
    local round_num="1"
    if [[ "${2:-}" =~ ^[0-9]+$ ]]; then
        round_num="$2"
        shift 2
    else
        shift 1
    fi
    export CLAUDE_PLUGIN_ROOT="$ROOT"
    export LARCH_QUIET_DISABLE=1
    export LARCH_PLAN_REVIEW_SCOUT_SH="$STUB/scout-plan-archetypes-wrapper.sh"
    export LARCH_PLAN_REVIEW_DISPATCH_PANEL_SH="$STUB/dispatch-plan-review-panel.sh"
    export LARCH_PLAN_REVIEW_COLLECT_SH="$STUB/collect-agent-results.sh"
    export LARCH_PLAN_REVIEW_DISPATCH_VOTERS_SH="$STUB/dispatch-plan-voters.sh"
    export LARCH_PLAN_REVIEW_TALLY_SH="${LARCH_PLAN_REVIEW_TALLY_SH:-$ROOT/skills/design/scripts/tally-plan-review.sh}"
    export LARCH_AGGREGATOR_DISABLED=1
    bash "$PLR" \
        --design-tmpdir "$d" \
        --plan-file "$d/plan.txt" \
        --feature-file "$d/feature-description.txt" \
        --codex-present true \
        --cursor-present true \
        --round-num "$round_num" \
        "$@"
}

echo "=== collector stderr is forwarded and captured ==="
DSTD="$TMP/collector-stderr"
mkdir -p "$DSTD"
printf 'plan\n\ndiff_lines: 1\n' >"$DSTD/plan.txt"
printf 'feat\n' >"$DSTD/feature-description.txt"
write_scout
write_dispatch_one_slot
cat >"$STUB/collect-agent-results.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
paths=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --paths-file) paths="${2:?}"; shift 2 ;;
        --timeout) shift 2 ;;
        --substantive-validation|--validation-mode|--structured-reviewer-validation) shift 1 ;;
        *) shift 1 ;;
    esac
done
printf 'collector stderr marker\n' >&2
while IFS= read -r p || [[ -n "$p" ]]; do
    [[ -z "$p" ]] && continue
    {
        printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix"
        printf '%s\n' "in_scope	important	correctness	src/a	Collector stderr finding	scenario	fix"
    } >"${p}.tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
chmod +x "$STUB/collect-agent-results.sh"
write_voters_three
err_file="$DSTD/stderr.txt"
run_loop "$DSTD" >"$DSTD/stdout.txt" 2>"$err_file"
grep -Fq 'collector stderr marker' "$err_file" || fail "collector stderr was not forwarded"
grep -Fq 'collector stderr marker' "$DSTD/plan-review-collector.stderr" || fail "collector stderr was not captured"

echo "=== stubbed driver: COMBINED_FALLBACK_COUNT degrades zero-findings path ==="
DC="$TMP/zc"
mkdir -p "$DC"
printf 'plan\n' >"$DC/plan.txt"
printf 'feat\n' >"$DC/feature-description.txt"
write_scout
export PLAN_REVIEW_SCOUT_ARGV_LOG="$DC/scout-argv.log"
: >"$PLAN_REVIEW_SCOUT_ARGV_LOG"
write_dispatch_combined_threshold
write_collect empty
write_voters_three
outc=$(run_loop "$DC")
grep -Fq -- '--codex-present' "$DC/scout-argv.log" || fail "plan-review-loop must forward codex-present to scout wrapper"
grep -Fq -- '--cursor-present' "$DC/scout-argv.log" || fail "plan-review-loop must forward cursor-present to scout wrapper"
printf '%s\n' "$outc" | grep -q '^DEGRADED_PANEL=1$' || fail "expected DEGRADED_PANEL=1 when COMBINED_FALLBACK_COUNT crosses threshold on zero-findings path"
printf '%s\n' "$outc" | grep -q '^TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings$' || fail "expected skipped-empty-findings with combined threshold"

echo "=== stubbed driver: zero findings (empty TSV) ==="
D0="$TMP/z0"
mkdir -p "$D0"
printf 'plan\n' >"$D0/plan.txt"
printf 'feat\n' >"$D0/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect empty
write_voters_three
out0=$(run_loop "$D0")
printf '%s\n' "$out0" | grep -q '^TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings$' || fail "expected skipped-empty-findings TALLY kv"
printf '%s\n' "$out0" | grep -q '^WARN=plan-review-tsv:' || fail "expected WARN for empty TSV path"
[[ -f "$D0/ballot.txt" ]] || fail "ballot.txt missing on zero-findings path"
grep -q 'No findings were raised' "$D0/voting-tally.md" || fail "expected zero-findings tally prose"
[[ -f "$D0/plan-review/round-1/findings-classification.tsv" ]] || fail "zero-findings classification TSV missing"
[[ "$(wc -l < "$D0/plan-review/round-1/findings-classification.tsv" | tr -d ' ')" == "1" ]] || fail "zero-findings classification TSV should contain header only"

echo "=== stubbed driver: zero findings (no_issues_found sentinel) ==="
D0S="$TMP/z0s"
mkdir -p "$D0S"
printf 'plan\n' >"$D0S/plan.txt"
printf 'feat\n' >"$D0S/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect no_issues_sentinel
write_voters_three
out0s=$(run_loop "$D0S")
printf '%s\n' "$out0s" | grep -q '^TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings$' || fail "expected skipped-empty-findings for no_issues_found sentinel"
printf '%s\n' "$out0s" | grep -vq '^WARN=plan-review-tsv:' || fail "no_issues_found sentinel must not emit plan-review-tsv WARN"

echo "=== stubbed driver: one finding + real tally ==="
D1="$TMP/z1"
mkdir -p "$D1"
printf 'plan\n' >"$D1/plan.txt"
printf 'feat\n' >"$D1/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
out1=$(run_loop "$D1")
printf '%s\n' "$out1" | grep -q '^TALLY_PLAN_REVIEW_STATUS=ok$' || fail "expected ok tally status"
printf '%s\n' "$out1" | grep -q '^LOOP_STATUS=complete$' || fail "expected complete loop"
grep -q 'FINDING_1' "$D1/accepted-plan-findings.md" || fail "accepted finding missing"
[[ -f "$D1/plan-review/round-1/findings-classification.tsv" ]] || fail "classification TSV missing for real tally"

echo "=== stubbed driver: COMBINED_FALLBACK_COUNT degrades findings-present path ==="
D1C="$TMP/z1c"
mkdir -p "$D1C"
printf 'plan\n' >"$D1C/plan.txt"
printf 'feat\n' >"$D1C/feature-description.txt"
write_scout
write_dispatch_combined_threshold
write_collect one
write_voters_three
out1c=$(run_loop "$D1C")
printf '%s\n' "$out1c" | grep -q '^DEGRADED_PANEL=1$' || fail "expected DEGRADED_PANEL=1 when COMBINED_FALLBACK_COUNT crosses threshold with findings present"
printf '%s\n' "$out1c" | grep -q '^TALLY_PLAN_REVIEW_STATUS=ok$' || fail "expected ok tally status with findings present under combined threshold"

echo "=== stubbed driver: round-2 artifacts honor --round-num ==="
D1R2="$TMP/z1r2"
mkdir -p "$D1R2"
printf 'plan\n' >"$D1R2/plan.txt"
printf 'feat\n' >"$D1R2/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
out1r2=$(run_loop "$D1R2" 2)
printf '%s\n' "$out1r2" | grep -q '^ROUNDS_COMPLETED=2$' || fail "expected round-2 ROUNDS_COMPLETED kv"
[[ -f "$D1R2/plan-review/round-2/findings-classification.tsv" ]] || fail "round-2 classification TSV missing"
[[ ! -e "$D1R2/plan-review/round-1/findings-classification.tsv" ]] || fail "round-2 run must not write round-1 TSV"

echo "=== empty paths with DISPATCH_OK=true => zero-findings (not panel-failed) ==="
D1E="$TMP/z1e"
mkdir -p "$D1E"
printf 'plan\n' >"$D1E/plan.txt"
printf 'feat\n' >"$D1E/feature-description.txt"
write_scout
write_dispatch_empty_paths_ok
write_collect empty
write_voters_three
set +e
out1e=$(run_loop "$D1E")
rc1e=$?
set -e
[[ "$rc1e" -eq 0 ]] || fail "empty paths with DISPATCH_OK=true should exit 0"
printf '%s\n' "$out1e" | grep -q '^TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings$' || fail "expected skipped-empty-findings for empty paths dispatch"
printf '%s\n' "$out1e" | grep -vq '^LOOP_STATUS=panel-failed$' || fail "empty paths must not surface panel-failed"

echo "=== #3392: dropped slots are logged per-slot to execution-issues.md ==="
DDS="$TMP/dropped-slots"
mkdir -p "$DDS"
printf 'plan\n' >"$DDS/plan.txt"
printf 'feat\n' >"$DDS/feature-description.txt"
write_scout
write_dispatch_dropped_slots
write_collect empty
write_voters_three
set +e
outds=$(run_loop "$DDS")
rcds=$?
set -e
[[ "$rcds" -eq 0 ]] || fail "dropped-slots round should exit 0 (DISPATCH_OK=true)"
[[ -f "$DDS/execution-issues.md" ]] || fail "dropped slots must create execution-issues.md"
grep -Fq 'External Reviewer Issues' "$DDS/execution-issues.md" || fail "dropped-slot entries must land under External Reviewer Issues"
grep -Fq 'format-gate-miss' "$DDS/execution-issues.md" || fail "execution-issues.md must record the format-gate-miss reason"
grep -Fq 'cursor-plan-arch' "$DDS/execution-issues.md" || fail "execution-issues.md must name the dropped cursor slot"
grep -Fq 'collector-failure' "$DDS/execution-issues.md" || fail "execution-issues.md must record the collector-failure reason"
grep -Fq 'Reviewing the plan against the repo' "$DDS/execution-issues.md" || fail "execution-issues.md must carry the offending snippet"
printf '%s\n' "$outds" | grep -Fq 'per-slot reasons recorded in execution-issues.md' || fail "aggregate WARN must point at the per-slot records"
printf '%s\n' "$outds" | grep -Fq 'dropped 2 slot(s)' || fail "aggregate WARN must report the dropped-slot count"

echo "=== both-absent generic Claude path reaches zero-findings tally ==="
D1G="$TMP/z1g"
mkdir -p "$D1G"
printf 'plan\n' >"$D1G/plan.txt"
printf 'feat\n' >"$D1G/feature-description.txt"
write_scout
write_dispatch_both_absent_generic
write_collect empty
write_voters_three
set +e
out1g=$(run_loop "$D1G" --codex-present false --cursor-present false)
rc1g=$?
set -e
[[ "$rc1g" -eq 0 ]] || fail "both-absent generic path should exit 0"
printf '%s\n' "$out1g" | grep -vq 'SENTINEL_TIMEOUT' || fail "both-absent generic path must not emit SENTINEL_TIMEOUT"
printf '%s\n' "$out1g" | grep -vq '^LOOP_STATUS=panel-failed$' || fail "both-absent generic path must not surface panel-failed"
printf '%s\n' "$out1g" | grep -q '^TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings$' || fail "expected skipped-empty-findings for both-absent generic path"

echo "=== codex-down cursor-only paths: collect without SENTINEL_TIMEOUT ==="
D1C="$TMP/z1c"
mkdir -p "$D1C"
printf 'plan\n' >"$D1C/plan.txt"
printf 'feat\n' >"$D1C/feature-description.txt"
write_scout
write_dispatch_cursor_only
write_collect_no_sentinel_timeout
write_voters_three
out1c=$(run_loop "$D1C" --codex-present false --cursor-present true)
printf '%s\n' "$out1c" | grep -vq 'SENTINEL_TIMEOUT' || fail "codex-down collect path must not emit SENTINEL_TIMEOUT"
printf '%s\n' "$out1c" | grep -vq '^LOOP_STATUS=panel-failed$' || fail "codex-down must not surface panel-failed"
printf '%s\n' "$out1c" | grep -q '^LOOP_STATUS=complete$' || fail "expected complete for cursor-only collect"

echo "=== real panel dispatch + collect with stubbed externals only ==="
export WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05
export RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05
export LARCH_TRANSIENT_RETRY_DELAY=0
DREAL="$TMP/zreal"
mkdir -p "$DREAL"
printf '## Plan\n\nDo thing.\n\ndiff_lines: 1\n' >"$DREAL/plan.txt"
printf 'feat\n' >"$DREAL/feature-description.txt"
EXTSTUB="$TMP/ext-stub-bin"
mkdir -p "$EXTSTUB"
cat >"$EXTSTUB/cursor" <<'EXTCUR'
#!/usr/bin/env bash
out=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output" ]]; then out="$arg"; fi
    last="$arg"
done
[[ -n "$out" ]] || exit 8
mkdir -p "$(dirname "$out")"
printf '{"no_issues_found": true}\n' >"$out"
printf '0\n' >"${out}.done"
EXTCUR
cat >"$EXTSTUB/codex" <<'EXTCOD'
#!/usr/bin/env bash
exit 7
EXTCOD
chmod +x "$EXTSTUB/cursor" "$EXTSTUB/codex"
write_scout
export LARCH_PLAN_REVIEW_DISPATCH_PANEL_SH="$ROOT/skills/design/scripts/dispatch-plan-review-panel.sh"
export LARCH_PLAN_REVIEW_COLLECT_SH="$ROOT/scripts/collect-agent-results.sh"
write_voters_three
out_real=$(PATH="$EXTSTUB:$PATH" run_loop "$DREAL" --codex-present false --cursor-present true --timeout 30)
printf '%s\n' "$out_real" | grep -vq 'SENTINEL_TIMEOUT' || fail "real panel/collect path must not emit SENTINEL_TIMEOUT"
printf '%s\n' "$out_real" | grep -vq '^LOOP_STATUS=panel-failed$' || fail "real panel/collect path must not surface panel-failed"
printf '%s\n' "$out_real" | grep -q '^TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings$' \
    || fail "real panel/collect path should reach skipped-empty-findings with no_issues_found outputs"
unset LARCH_PLAN_REVIEW_DISPATCH_PANEL_SH LARCH_PLAN_REVIEW_COLLECT_SH

echo "=== panel-failed path writes header-only classification TSV ==="
D1P="$TMP/z1p"
mkdir -p "$D1P"
printf 'plan\n' >"$D1P/plan.txt"
printf 'feat\n' >"$D1P/feature-description.txt"
write_scout
write_dispatch_fail
write_collect one
write_voters_three
set +e
out1p=$(run_loop "$D1P")
rc1p=$?
set -e
[[ "$rc1p" -eq 1 ]] || fail "panel-failed path should exit 1"
printf '%s\n' "$out1p" | grep -q '^LOOP_STATUS=panel-failed$' || fail "expected panel-failed loop status"
[[ -f "$D1P/plan-review/round-1/findings-classification.tsv" ]] || fail "panel-failed classification TSV missing"
[[ "$(wc -l < "$D1P/plan-review/round-1/findings-classification.tsv" | tr -d ' ')" == "1" ]] || fail "panel-failed TSV should contain header only"
assert_plan_round_timing_row "$D1P" 1

echo "=== stubbed driver: failed middle voter preserves canonical tally slot ==="
D1B="$TMP/z1b"
mkdir -p "$D1B"
printf 'plan\n' >"$D1B/plan.txt"
printf 'feat\n' >"$D1B/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_slot2_failed
out1b=$(run_loop "$D1B")
printf '%s\n' "$out1b" | grep -q '^TALLY_PLAN_REVIEW_STATUS=ok$' || fail "expected ok tally status with failed middle voter"
python3 - "$D1B/plan-review/round-1/findings-classification.tsv" <<'PY'
import csv, sys
with open(sys.argv[1], newline="", encoding="utf-8") as fh:
    row = next(csv.DictReader(fh, delimiter="\t"))
assert row["finding_id"] == "FINDING_1"
assert row["v1_tool"] == "Claude"
assert row["v2_tool"] == ""
assert row["v3_tool"] == "Cursor"
PY

echo "=== brainstorm context stays non-binding while staged scope anchor dispatches ==="
DB="$TMP/zb"
mkdir -p "$DB"
printf 'plan\n' >"$DB/plan.txt"
printf 'feat base\n' >"$DB/feature-description.txt"
cat >"$DB/brainstorm.md" <<'EOS'
## Brainstorm Synthesis

### Idea
**Source:** claude-brainstorm
extra context
EOS
write_scout
write_dispatch_one_slot
write_collect one
export PLAN_REVIEW_SCOUT_ARGV_LOG="$DB/scout-argv.log"
: >"$PLAN_REVIEW_SCOUT_ARGV_LOG"
export PLAN_REVIEW_VOTER_ARGV_LOG="$DB/voter-argv.log"
: >"$PLAN_REVIEW_VOTER_ARGV_LOG"
write_voters_three
outb=$(run_loop "$DB")
printf '%s\n' "$outb" | grep -q '^TALLY_PLAN_REVIEW_STATUS=ok$' || fail "expected ok tally status with brainstorm merge"
grep -Fq 'feat base' "$DB/feature-file-seen.txt" || fail "scope anchor missing base content"
if grep -Fq 'extra context' "$DB/feature-file-seen.txt"; then fail "binding scope anchor should not include brainstorm content"; fi
python3 - "$DB/plan-review-scope-anchor.txt" "$DB/feature-file-path.txt" <<'PY' || fail "panel should receive staged scope anchor path"
import os, sys
expected = os.path.realpath(sys.argv[1])
actual = os.path.realpath(open(sys.argv[2], encoding="utf-8").read().strip())
if expected != actual:
    raise SystemExit(1)
PY
grep -Fq '## Feature / issue context (base)' "$DB/plan-review-feature-context.txt" || fail "non-binding brainstorm context missing base header"
grep -Fq '## Brainstorm synthesis (additive; optional, non-binding)' "$DB/plan-review-feature-context.txt" || fail "non-binding brainstorm context missing brainstorm header"
grep -Fq 'extra context' "$DB/plan-review-feature-context.txt" || fail "non-binding brainstorm context missing brainstorm content"
grep -Fq -- '--description-file' "$DB/scout-argv.log" || fail "scout argv missing --description-file"
grep -Fq 'plan-review-scope-anchor.txt' "$DB/scout-argv.log" || fail "scout argv missing raw staged scope anchor path"
grep -Fq -- '--scope-anchor-file' "$DB/voter-argv.log" || fail "voter argv missing --scope-anchor-file"
grep -Fq 'plan-review-scope-anchor.txt' "$DB/voter-argv.log" || fail "voter argv missing staged scope anchor path"

echo "=== stubbed tally failure still emits loop KVs ==="
D2="$TMP/z2"
mkdir -p "$D2"
cp "$D1/plan.txt" "$D2/plan.txt"
cp "$D1/feature-description.txt" "$D2/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
write_tally_fail
_prev_tally="${LARCH_PLAN_REVIEW_TALLY_SH:-}"
export LARCH_PLAN_REVIEW_TALLY_SH="$STUB/tally-plan-review.sh"
out2=$(run_loop "$D2")
if [[ -n "$_prev_tally" ]]; then
    export LARCH_PLAN_REVIEW_TALLY_SH="$_prev_tally"
else
    unset LARCH_PLAN_REVIEW_TALLY_SH
fi
printf '%s\n' "$out2" | grep -q '^TALLY_PLAN_REVIEW_STATUS=tally-error$' || fail "expected tally-error after stub tally rc=2"
printf '%s\n' "$out2" | grep -q '^LOOP_STATUS=tally-error$' || fail "expected tally-error loop after tally failure"
printf '%s\n' "$out2" | grep -q '^WARN=plan-review-tally:' || fail "expected tally WARN"
[[ -f "$D2/voting-tally.md" ]] || fail "voting-tally.md missing after stub tally failure"
[[ -s "$D2/voting-tally.md" ]] || fail "voting-tally.md empty after stub tally failure"
grep -q 'Tally aborted' "$D2/voting-tally.md" || fail "stub tally banner missing in voting-tally.md"
[[ -f "$D2/plan-review/round-1/findings-classification.tsv" ]] || fail "classification TSV missing after stub tally failure"
[[ "$(wc -l < "$D2/plan-review/round-1/findings-classification.tsv" | tr -d ' ')" == "1" ]] || fail "tally-error TSV should contain header only"

echo "=== stubbed driver: three reviewers each OOS_1 + FINDING_1 (dedup + tally) ==="
D3="$TMP/z3"
mkdir -p "$D3"
printf 'plan\n' >"$D3/plan.txt"
printf 'feat\n' >"$D3/feature-description.txt"
write_scout
write_dispatch_three_slots
write_collect three_distinct
write_voters_plan_six
out3=$(run_loop "$D3")
printf '%s\n' "$out3" | grep -q '^TALLY_PLAN_REVIEW_STATUS=ok$' || fail "expected ok tally status (three-reviewer case)"
printf '%s\n' "$out3" | grep -q '^LOOP_STATUS=complete$' || fail "expected complete loop (three-reviewer case)"
[[ -s "$D3/ballot.txt" ]] || fail "ballot.txt missing or empty (three-reviewer case)"
for _h in "### OOS_1:" "### OOS_2:" "### OOS_3:"; do
    _c=$(grep -cF "$_h" "$D3/findings.md" 2>/dev/null || true)
    [[ "$_c" -eq 1 ]] || fail "expected exactly one $_h in findings.md, got $_c"
    _b=$(grep -cF "$_h" "$D3/ballot.txt" 2>/dev/null || true)
    [[ "$_b" -eq 1 ]] || fail "expected exactly one $_h in ballot.txt, got $_b"
done
python3 - "$D3/findings.md" <<'PY' || fail "FINDING heading ids not strictly increasing from 1 in findings.md"
import re, sys

path = sys.argv[1]
text = open(path, encoding="utf-8", errors="replace").read()
nums = [int(m.group(1)) for m in re.finditer(r"^### FINDING_(\d+):", text, re.M)]
if not nums:
    print("no FINDING headings", file=sys.stderr)
    sys.exit(1)
if nums[0] != 1:
    print("FINDING ids must start at 1", file=sys.stderr)
    sys.exit(1)
for a, b in zip(nums, nums[1:]):
    if b <= a:
        print(f"not strictly increasing: {nums}", file=sys.stderr)
        sys.exit(1)
PY

echo "=== legacy single-pass: no --round-cap → LOOP_STATUS=complete ==="
DL="$TMP/legacy"
mkdir -p "$DL"
printf 'plan v1\n\ndiff_lines: 1\n' >"$DL/plan.txt"
printf 'feat\n' >"$DL/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
out_legacy=$(run_loop "$DL" 1)
printf '%s\n' "$out_legacy" | grep -q '^LOOP_STATUS=complete$' || fail "legacy mode expected complete"
[[ -f "$DL/.step3-plan-review-result.env" ]] || fail "legacy missing step3 result env"
! grep -q '^REASON=manual-gate-b$' "$DL/.step3-plan-review-result.env" || fail "legacy should not be manual-gate-b"

echo "=== legacy single-pass: env-only LARCH_DESIGN_ROUND_CAP does not enable multi-round ==="
DLENV="$TMP/legacy-env"
mkdir -p "$DLENV"
printf 'plan v1\n\ndiff_lines: 1\n' >"$DLENV/plan.txt"
printf 'feat\n' >"$DLENV/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
out_legacy_env=$(LARCH_DESIGN_ROUND_CAP=7 run_loop "$DLENV" 1)
printf '%s\n' "$out_legacy_env" | grep -q '^LOOP_STATUS=complete$' || fail "env-only round cap should remain legacy complete"

echo "=== legacy single-pass: file layout stays golden ==="
DLEG="$TMP/legacy-golden"
mkdir -p "$DLEG"
printf 'plan\n' >"$DLEG/plan.txt"
printf 'feat\n' >"$DLEG/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
out_leg=$(run_loop "$DLEG")
printf '%s\n' "$out_leg" | grep -q '^LOOP_STATUS=complete$' || fail "legacy golden case should complete"
actual_legacy_layout=$(sorted_file_list "$DLEG")
actual_legacy_layout=${actual_legacy_layout//$'\ndirty-tree-detected.env'/}
expected_legacy_layout=$'.step3-plan-review-result.env\naccepted-plan-findings.md\nballot.txt\ncursor-plan-arch-output.txt\ncursor-plan-arch-output.txt.tsv\nfeature-description.txt\nfeature-file-path.txt\nfeature-file-seen.txt\nfindings-in-scope.md\nfindings-in-scope.pre-dedup.md\nfindings-oos.md\nfindings-oos.pre-dedup.md\nfindings.md\nfindings.md.tmp\noos-this-round.md\noos.md\npanel-paths.txt\nplan-review-collector.stderr\nplan-review-scope-anchor.txt\nplan-review-slots.ndjson\nplan-review/round-1/accepted-plan-findings.md\nplan-review/round-1/ballot.txt\nplan-review/round-1/findings-classification.tsv\nplan-review/round-1/findings-in-scope.md\nplan-review/round-1/findings-in-scope.pre-dedup.md\nplan-review/round-1/findings-oos.md\nplan-review/round-1/findings.md\nplan-review/round-1/oos-accepted-design.md\nplan-review/round-1/oos.md\nplan-review/round-1/plan-review-scope-anchor.txt\nplan-review/round-1/plan-review-slots.ndjson\nplan-review/round-1/plan.txt\nplan-review/round-1/rejected-findings.md\nplan-review/round-1/round-summary.env\nplan-review/round-1/scout-plan-manifest.json\nplan-review/round-1/voting-tally.md\nplan.txt\nrejected-findings.md\nrender-plan-cursor-arch.prompt\nscout-plan-manifest.json\ntiming-ledger.tsv\ntiming-ledger.tsv.lock\nvoter-paths.list\nvoting-tally.md\nvstub1.txt\nvstub2.txt\nvstub3.txt'
[[ "$actual_legacy_layout" == "$expected_legacy_layout" ]] || fail "legacy file layout drifted: $actual_legacy_layout"
[[ ! -d "$DLENV/plan-review/round-1/revise" ]] || fail "env-only round cap should not create revise artifacts"

echo "=== single-pass: zero findings + collector OK → complete ==="
DZ="$TMP/single-zero"
mkdir -p "$DZ"
printf 'plan\n\ndiff_lines: 1\n' >"$DZ/plan.txt"
printf 'feat\n' >"$DZ/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect_no_findings
write_voters_three
out_z=$(run_loop "$DZ" 1 --round-cap 3)
printf '%s\n' "$out_z" | grep -q '^LOOP_STATUS=complete$' || fail "expected single-pass complete for zero findings"
printf '%s\n' "$out_z" | grep -q '^REVISE_STATUS=skipped$' || fail "single-pass should not revise"
assert_plan_round_timing_row "$DZ" 1


echo "=== single-pass: zero findings + degraded panel stays zero-findings-degraded-panel ==="
DZD="$TMP/single-zero-degraded"
mkdir -p "$DZD"
printf 'plan\n\ndiff_lines: 1\n' >"$DZD/plan.txt"
printf 'feat\n' >"$DZD/feature-description.txt"
write_scout
write_dispatch_degraded
write_collect_no_findings
write_voters_three
out_zd=$(run_loop "$DZD" 1 --round-cap 3)
printf '%s\n' "$out_zd" | grep -q '^LOOP_STATUS=zero-findings-degraded-panel$' || fail "degraded zero findings should stay degraded"


echo "=== single-pass: zero findings + no collector OK → degraded-empty-collector ==="
DZ0="$TMP/single-zero-no-collector"
mkdir -p "$DZ0"
printf 'plan\n\ndiff_lines: 1\n' >"$DZ0/plan.txt"
printf 'feat\n' >"$DZ0/feature-description.txt"
write_scout
write_dispatch_no_paths_degraded
write_collect_no_findings
write_voters_three
out_z0=$(run_loop "$DZ0" 1 --round-cap 3)
printf '%s\n' "$out_z0" | grep -q '^LOOP_STATUS=degraded-empty-collector$' || fail "no collector OK should surface degraded-empty-collector"


echo "=== single-pass: accepted OOS accumulation excludes rejected OOS ==="
DOOS="$TMP/single-oos"
mkdir -p "$DOOS"
printf 'plan\n\ndiff_lines: 1\n' >"$DOOS/plan.txt"
printf 'feat\n' >"$DOOS/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect_important_with_oos
write_voters_three
out_oos=$(run_loop "$DOOS" 1 --round-cap 2)
printf '%s\n' "$out_oos" | grep -q '^LOOP_STATUS=complete$' || fail "OOS filter path should complete"
grep -q 'accepted OOS' "$DOOS/oos-accepted-design.md" || fail "accepted OOS missing"
! grep -q 'rejected OOS' "$DOOS/oos-accepted-design.md" || fail "rejected OOS leaked into accepted OOS"


echo "=== single-pass: main-agent-vote-required preserves accepted OOS artifact ==="
DMA="$TMP/single-main-agent"
mkdir -p "$DMA"
printf 'plan\n\ndiff_lines: 1\n' >"$DMA/plan.txt"
printf 'feat\n' >"$DMA/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect_important_with_oos
write_voters_three
write_tally_main_agent
out_ma=$(run_loop "$DMA" 1 --round-cap 2)
printf '%s\n' "$out_ma" | grep -q '^LOOP_STATUS=main-agent-vote-required$' || fail "main-agent status should be preserved"
grep -q 'accepted OOS' "$DMA/oos-accepted-design.md" || fail "main-agent OOS accumulation missing"


echo "=== single-pass: tally-error exits before terminal fallback ==="
DTM="$TMP/single-tally-error"
mkdir -p "$DTM"
printf 'plan\n\ndiff_lines: 1\n' >"$DTM/plan.txt"
printf 'feat\n' >"$DTM/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect_important
write_voters_three
write_tally_error
out_tm=$(run_loop "$DTM" 1 --round-cap 2)
printf '%s\n' "$out_tm" | grep -q '^LOOP_STATUS=tally-error$' || fail "tally-error should surface tally-error loop status"
printf '%s\n' "$out_tm" | grep -q '^REVISE_STATUS=skipped$' || fail "tally-error should skip revise"

echo "=== stubbed driver: empty collector stdout fails closed (panel-failed) ==="
DEMPTY="$TMP/collector-empty-fail"
mkdir -p "$DEMPTY"
printf 'plan\n' >"$DEMPTY/plan.txt"
printf 'feat\n' >"$DEMPTY/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect_empty_fail
write_voters_three
set +e
out_empty=$(run_loop "$DEMPTY")
empty_rc=$?
set -e
[[ "$empty_rc" -eq 1 ]] || fail "empty collector failure should exit 1"
if printf '%s\n' "$out_empty" | grep -q '^LOOP_STATUS=panel-failed$'; then
    :
elif grep -Fq 'collector failed with empty stdout' "$DEMPTY/voting-tally.md" 2>/dev/null \
    && [[ -f "$DEMPTY/plan-review/round-1/findings-classification.tsv" ]]; then
    :
else
    fail "empty collector failure should fail closed (rc=$empty_rc out=$out_empty)"
fi

echo "=== stubbed driver: collector stderr tail reaches quiet tee log (#3227) ==="
DQUIET="$TMP/stderr-tail-fd4-quiet"
mkdir -p "$DQUIET"
printf 'plan\n' >"$DQUIET/plan.txt"
printf 'feat\n' >"$DQUIET/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect_failing_tail
write_voters_three
set +e
(
    export CLAUDE_PLUGIN_ROOT="$ROOT"
    export LARCH_PLAN_REVIEW_SCOUT_SH="$STUB/scout-plan-archetypes-wrapper.sh"
    export LARCH_PLAN_REVIEW_DISPATCH_PANEL_SH="$STUB/dispatch-plan-review-panel.sh"
    export LARCH_PLAN_REVIEW_COLLECT_SH="$STUB/collect-agent-results.sh"
    export LARCH_PLAN_REVIEW_DISPATCH_VOTERS_SH="$STUB/dispatch-plan-voters.sh"
    export LARCH_PLAN_REVIEW_TALLY_SH="${LARCH_PLAN_REVIEW_TALLY_SH:-$ROOT/skills/design/scripts/tally-plan-review.sh}"
    export LARCH_AGGREGATOR_DISABLED=1
    unset LARCH_QUIET_DISABLE
    bash "$PLR" \
        --design-tmpdir "$DQUIET" \
        --plan-file "$DQUIET/plan.txt" \
        --feature-file "$DQUIET/feature-description.txt" \
        --codex-present true \
        --cursor-present true \
        --round-num 1
) >"$DQUIET/loop.stdout" 2>"$DQUIET/loop.stderr"
quiet_rc=$?
set -e
[[ "$quiet_rc" -eq 0 ]] || fail "quiet collector stderr tail loop should exit 0"
grep -Fq 'LARCH_TEST_STDERR_TAIL_MARKER' "$DQUIET/plan-review-collector.stderr" \
    || fail "stderr tail marker must reach plan-review-collector.stderr under quiet"

printf '%s\n' "test-plan-review-loop: ok"
