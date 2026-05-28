#!/usr/bin/env bash
# Offline integration tests for plan-review-loop.sh (PATH-style stubs via LARCH_PLAN_REVIEW_*_SH).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
PLR="$ROOT/skills/design/scripts/plan-review-loop.sh"

fail() { printf '%s\n' "$1" >&2; exit 1; }

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
[[ "$rc" == 2 ]] || fail "expected exit 2 when --round-num exceeds --round-cap, got $rc"

write_scout() {
    cat >"$STUB/scout-plan-archetypes-wrapper.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) out="${2:?}"; shift 2 ;;
        --plan-file|--description-file|--max-archetypes|--session-env-path) shift 2 ;;
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

write_collect_one_nit() {
    write_collect one_nit
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
        printf '%s\n' "out_of_scope	important	correctness	src/oos1	Accepted OOS problem	scenario accepted	fix accepted"
        printf '%s\n' "out_of_scope	important	correctness	src/oos2	Rejected OOS problem	scenario rejected	fix rejected"
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

write_voters_three() {
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
for f in "$v1" "$v2" "$v3"; do
    cat >"$f" <<'INNER'
FINDING_1: YES
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
- **Description**: Main-agent branch OOS. Scenario: branch coverage
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
    export LARCH_PLAN_REVIEW_REVISE_SH="${LARCH_PLAN_REVIEW_REVISE_SH:-$ROOT/skills/design/scripts/revise-plan-with-waterfall.sh}"
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

echo "=== stubbed driver: COMBINED_FALLBACK_COUNT degrades zero-findings path ==="
DC="$TMP/zc"
mkdir -p "$DC"
printf 'plan\n' >"$DC/plan.txt"
printf 'feat\n' >"$DC/feature-description.txt"
write_scout
write_dispatch_combined_threshold
write_collect empty
write_voters_three
outc=$(run_loop "$DC")
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

echo "=== brainstorm context merges into feature file before dispatch ==="
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
write_voters_three
outb=$(run_loop "$DB")
printf '%s\n' "$outb" | grep -q '^TALLY_PLAN_REVIEW_STATUS=ok$' || fail "expected ok tally status with brainstorm merge"
grep -Fq '## Feature / issue context (base)' "$DB/feature-file-seen.txt" || fail "merged feature file missing base header"
grep -Fq 'feat base' "$DB/feature-file-seen.txt" || fail "merged feature file missing base content"
grep -Fq '## Brainstorm synthesis (additive; optional)' "$DB/feature-file-seen.txt" || fail "merged feature file missing brainstorm header"
grep -Fq 'extra context' "$DB/feature-file-seen.txt" || fail "merged feature file missing brainstorm content"

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
printf '%s\n' "$out2" | grep -q '^LOOP_STATUS=complete$' || fail "expected complete loop after tally failure"
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
expected_legacy_layout=$'.step3-plan-review-result.env\naccepted-plan-findings.md\nballot.txt\ncursor-plan-arch-output.txt\ncursor-plan-arch-output.txt.tsv\nfeature-description.txt\nfeature-file-path.txt\nfeature-file-seen.txt\nfindings-in-scope.md\nfindings-oos.md\nfindings.md\nfindings.md.tmp\noos-accepted-design.md\noos.md\npanel-paths.txt\nplan-review-slots.ndjson\nplan-review/round-1/findings-classification.tsv\nplan.txt\nrejected-findings.md\nrender-plan-cursor-arch.prompt\nscout-plan-manifest.json\nvoter-paths.list\nvoting-tally.md\nvstub1.txt\nvstub2.txt\nvstub3.txt'
[[ "$actual_legacy_layout" == "$expected_legacy_layout" ]] || fail "legacy file layout drifted: $actual_legacy_layout"
[[ ! -d "$DLENV/plan-review/round-1/revise" ]] || fail "env-only round cap should not create revise artifacts"

echo "=== multi-round: zero findings + collector OK → converged zero-findings ==="
DZ="$TMP/mrz"
mkdir -p "$DZ"
printf 'plan\n\ndiff_lines: 1\n' >"$DZ/plan.txt"
printf 'feat\n' >"$DZ/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect empty
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=ok\n'
exit 0
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_z=$(run_loop "$DZ" 1 --round-cap 3 --convergence-threshold 3)
printf '%s\n' "$out_z" | grep -q '^LOOP_STATUS=converged$' || fail "expected converged zero-findings"
printf '%s\n' "$out_z" | grep -q '^REASON=zero-findings$' || fail "expected zero-findings reason"

echo "=== multi-round: zero findings + degraded panel stays non-converged ==="
DZD="$TMP/mrzd"
mkdir -p "$DZD"
printf 'plan\n\ndiff_lines: 1\n' >"$DZD/plan.txt"
printf 'feat\n' >"$DZD/feature-description.txt"
write_scout
write_dispatch_combined_threshold
write_collect empty
write_voters_three
out_zd=$(run_loop "$DZD" 1 --round-cap 3 --convergence-threshold 3)
printf '%s\n' "$out_zd" | grep -q '^LOOP_STATUS=zero-findings-degraded-panel$' || fail "degraded zero-findings should use dedicated loop status"
printf '%s\n' "$out_zd" | grep -q '^REASON=zero-findings-degraded-panel$' || fail "expected degraded zero-findings reason"

echo "=== multi-round: zero findings + no collector OK → degraded-empty-collector ==="
DZ0="$TMP/mrz0"
mkdir -p "$DZ0"
printf 'plan\n\ndiff_lines: 1\n' >"$DZ0/plan.txt"
printf 'feat\n' >"$DZ0/feature-description.txt"
write_scout
write_dispatch_one_slot
cat >"$STUB/collect-agent-results.sh" <<'EOS'
#!/usr/bin/env bash
paths=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --paths-file) paths="${2:?}"; shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$paths" && -f "$paths" ]] || exit 1
while IFS= read -r p || [[ -n "$p" ]]; do
    [[ -z "$p" ]] && continue
    tsv="${p}.tsv"
    printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix" >"$tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=failed\nEXIT_CODE=1\n\n' "$p"
done <"$paths"
EOS
chmod +x "$STUB/collect-agent-results.sh"
write_voters_three
out_z0=$(run_loop "$DZ0" 1 --round-cap 3)
printf '%s\n' "$out_z0" | grep -q '^LOOP_STATUS=degraded-empty-collector$' || fail "expected degraded-empty-collector"

echo "=== multi-round: accepted OOS accumulation excludes rejected OOS ==="
DOOS="$TMP/mr-oos-filter"
mkdir -p "$DOOS"
printf 'plan\n\ndiff_lines: 1\n' >"$DOOS/plan.txt"
printf 'feat\n' >"$DOOS/feature-description.txt"
printf '{"manual_gate_b":true}\n' >"$DOOS/run-params.json"
write_scout
write_dispatch_one_slot
write_collect_with_oos_votes
write_voters_with_oos_split
out_oos=$(run_loop "$DOOS" 1 --round-cap 2)
printf '%s\n' "$out_oos" | grep -q '^LOOP_STATUS=complete$' || fail "manual OOS filter path should complete"
grep -q 'Accepted OOS problem' "$DOOS/oos-accepted-design.md" || fail "accepted OOS must remain in cumulative file"
if grep -q 'Rejected OOS problem' "$DOOS/oos-accepted-design.md"; then
    fail "rejected OOS must not enter cumulative file"
fi

echo "=== multi-round: cumulative accepted OOS survives later rounds ==="
DOOSC="$TMP/mr-oos-cumulative"
mkdir -p "$DOOSC"
printf 'plan\n\ndiff_lines: 1\n' >"$DOOSC/plan.txt"
printf 'feat\n' >"$DOOSC/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect_distinct_oos_per_round
write_voters_with_oos_split
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_oosc=$(run_loop "$DOOSC" 1 --round-cap 2 --convergence-threshold 0)
printf '%s\n' "$out_oosc" | grep -q '^LOOP_STATUS=cap-hit$' || fail "two accepted rounds should cap-hit"
grep -q 'Round 1 accepted OOS' "$DOOSC/oos-accepted-design.md" || fail "round 1 accepted OOS missing from cumulative file"
grep -q 'Round 2 accepted OOS' "$DOOSC/oos-accepted-design.md" || fail "round 2 accepted OOS missing from cumulative file"

echo "=== multi-round: duplicate accepted OOS descriptions dedup across rounds ==="
DOOSD="$TMP/mr-oos-dedup"
mkdir -p "$DOOSD"
printf 'plan\n\ndiff_lines: 1\n' >"$DOOSD/plan.txt"
printf 'feat\n' >"$DOOSD/feature-description.txt"
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
        printf '%s\n' "out_of_scope	important	correctness	src/oos	Duplicate OOS description across rounds	shared scenario	shared fix"
    } >"$tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
chmod +x "$STUB/collect-agent-results.sh"
write_voters_with_oos_split
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_oosd=$(run_loop "$DOOSD" 1 --round-cap 2 --convergence-threshold 0)
printf '%s\n' "$out_oosd" | grep -q '^LOOP_STATUS=cap-hit$' || fail "duplicate OOS dedup case should cap-hit"
[[ "$(grep -c '^### OOS_' "$DOOSD/oos-accepted-design.md" | tr -d ' ')" == "1" ]] || fail "duplicate accepted OOS should only appear once cumulatively"

echo "=== multi-round: distinct accepted OOS descriptions must not dedup by substring ==="
DOOSS="$TMP/mr-oos-substring"
mkdir -p "$DOOSS"
printf 'plan\n\ndiff_lines: 1\n' >"$DOOSS/plan.txt"
printf 'feat\n' >"$DOOSS/feature-description.txt"
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
        if [[ "$round" == "1" ]]; then
            printf '%s\n' "out_of_scope	important	correctness	src/oos1	Shared phrase	scenario one	fix one"
        else
            printf '%s\n' "out_of_scope	important	correctness	src/oos2	Shared phrase with follow-up detail	scenario two	fix two"
        fi
    } >"$tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
chmod +x "$STUB/collect-agent-results.sh"
write_voters_with_oos_split
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_ooss=$(run_loop "$DOOSS" 1 --round-cap 2 --convergence-threshold 0)
printf '%s\n' "$out_ooss" | grep -q '^LOOP_STATUS=cap-hit$' || fail "substring-distinct OOS case should cap-hit"
[[ "$(grep -c '^### OOS_' "$DOOSS/oos-accepted-design.md" | tr -d ' ')" == "2" ]] || fail "substring-distinct accepted OOS entries must both survive cumulatively"

echo "=== multi-round: manual_gate_b → complete manual-gate-b, revise not required ==="
DM="$TMP/manual"
mkdir -p "$DM"
printf 'plan\n\ndiff_lines: 1\n' >"$DM/plan.txt"
printf 'feat\n' >"$DM/feature-description.txt"
printf '{"manual_gate_b":true}\n' >"$DM/run-params.json"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
_revise_called=false
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
echo "revise should not run" >&2
exit 99
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_m=$(run_loop "$DM" 1 --round-cap 5)
printf '%s\n' "$out_m" | grep -q '^LOOP_STATUS=complete$' || fail "manual mode expected complete"
printf '%s\n' "$out_m" | grep -q '^REASON=manual-gate-b$' || fail "manual mode expected manual-gate-b reason"

echo "=== multi-round: manual_gate_b true survives malformed JSON fallback ==="
DMB="$TMP/manual-bad-json"
mkdir -p "$DMB"
printf 'plan\n\ndiff_lines: 1\n' >"$DMB/plan.txt"
printf 'feat\n' >"$DMB/feature-description.txt"
printf '{"manual_gate_b": true,\n' >"$DMB/run-params.json"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
echo "revise should not run for malformed-json manual mode" >&2
exit 99
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_mb=$(run_loop "$DMB" 1 --round-cap 2)
printf '%s\n' "$out_mb" | grep -q '^REASON=manual-gate-b$' || fail "manual JSON fallback should preserve manual-gate-b"

echo "=== multi-round: main-agent-vote-required preserves accepted OOS artifact ==="
DMA="$TMP/mr-main-agent"
mkdir -p "$DMA"
printf 'plan\n\ndiff_lines: 1\n' >"$DMA/plan.txt"
printf 'feat\n' >"$DMA/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
write_tally_main_agent_stub
export LARCH_PLAN_REVIEW_TALLY_SH="$STUB/tally-plan-review.sh"
out_ma=$(run_loop "$DMA" 1 --round-cap 2)
unset LARCH_PLAN_REVIEW_TALLY_SH
printf '%s\n' "$out_ma" | grep -q '^LOOP_STATUS=main-agent-vote-required$' || fail "main-agent stub should surface main-agent-vote-required"
grep -q 'Main-agent branch OOS' "$DMA/oos-accepted-design.md" || fail "main-agent branch must preserve accepted OOS artifact"

echo "=== multi-round: tally-error exits before revise ==="
DTM="$TMP/mr-tally"
mkdir -p "$DTM"
printf 'plan\n\ndiff_lines: 1\n' >"$DTM/plan.txt"
printf 'feat\n' >"$DTM/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
write_tally_fail
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
echo "revise should not run on tally-error" >&2
exit 99
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_TALLY_SH="$STUB/tally-plan-review.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_tm=$(run_loop "$DTM" 1 --round-cap 2 --convergence-threshold 3)
unset LARCH_PLAN_REVIEW_TALLY_SH
printf '%s\n' "$out_tm" | grep -q '^LOOP_STATUS=tally-error$' || fail "multi-round tally-error should surface tally-error loop status"
printf '%s\n' "$out_tm" | grep -q '^REVISE_STATUS=skipped$' || fail "multi-round tally-error should skip revise"
[[ -f "$DTM/.step3-plan-review-result.env" ]] || fail "multi-round tally-error missing result env"
grep -q '^LOOP_STATUS=tally-error$' "$DTM/.step3-plan-review-result.env" || fail "result env missing tally-error loop status"
assert_env_has_keys "$DTM/.step3-plan-review-result.env" LOOP_STATUS ACCEPTED_COUNT IMPORTANT_ACCEPTED_COUNT DEGRADED_PANEL ROUNDS_COMPLETED REASON REVISE_STATUS CONVERGENCE_STREAK AGGREGATOR_STATUS TALLY_PLAN_REVIEW_STATUS VOTING_TALLY_FILE VOTER_1_PARSE_RATE_STATUS COLLECT_OK_COUNT COLLECT_FAILURE_COUNT

echo "=== multi-round: revise failure returns revision-failed ==="
DRV="$TMP/mr-revise-fail"
mkdir -p "$DRV"
printf 'plan\n\ndiff_lines: 1\n' >"$DRV/plan.txt"
printf 'feat\n' >"$DRV/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=failed-no-patch\nREVISE_WINNING_TIER=\n'
exit 0
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_rv=$(run_loop "$DRV" 1 --round-cap 3 --convergence-threshold 3)
printf '%s\n' "$out_rv" | grep -q '^LOOP_STATUS=revision-failed$' || fail "revise failure should surface revision-failed"
printf '%s\n' "$out_rv" | grep -q '^REVISE_STATUS=failed-no-patch$' || fail "revise failure should preserve revise status"
grep -q '^REVISE_STATUS=failed-no-patch$' "$DRV/plan-review/round-1/round-summary.env" || fail "round summary should preserve revise failure status"

echo "=== multi-round: revise rc failure returns revision-failed + failed-apply ==="
DRC="$TMP/mr-revise-rc-fail"
mkdir -p "$DRC"
printf 'plan\n\ndiff_lines: 1\n' >"$DRC/plan.txt"
printf 'feat\n' >"$DRC/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
exit 7
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_rcf=$(run_loop "$DRC" 1 --round-cap 2)
printf '%s\n' "$out_rcf" | grep -q '^LOOP_STATUS=revision-failed$' || fail "revise rc failure should surface revision-failed"
printf '%s\n' "$out_rcf" | grep -q '^REVISE_STATUS=failed-apply$' || fail "revise rc failure should map to failed-apply"

echo "=== multi-round: emit-plan failure after revise surfaces emit-plan-failed ==="
DEF="$TMP/mr-emit-plan-fail"
mkdir -p "$DEF"
printf 'plan\n\ndiff_lines: 1\n' >"$DEF/plan.txt"
printf 'feat\n' >"$DEF/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        *) shift 2 ;;
    esac
done
printf '## Plan\n\nmissing trailer on purpose\n' >"$DESIGN_TMPDIR/plan.txt"
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_ep=$(run_loop "$DEF" 1 --round-cap 2 --convergence-threshold 3)
printf '%s\n' "$out_ep" | grep -q '^LOOP_STATUS=emit-plan-failed$' || fail "emit-plan failure should surface emit-plan-failed"
cmp -s "$DEF/plan.txt" <(printf 'plan\n\ndiff_lines: 1\n') || fail "emit-plan failure must restore the prior plan"

echo "=== multi-round: blank severity rows do not inflate important count ==="
DBS="$TMP/mr-blank-severity"
mkdir -p "$DBS"
printf 'plan\n\ndiff_lines: 1\n' >"$DBS/plan.txt"
printf 'feat\n' >"$DBS/feature-description.txt"
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
[[ -n "$paths" && -f "$paths" ]] || exit 1
while IFS= read -r p || [[ -n "$p" ]]; do
    [[ -z "$p" ]] && continue
    tsv="${p}.tsv"
    {
        printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix"
        printf '%s\n' "in_scope		correctness	src/a	Blank severity finding	scenario	fix"
    } >"$tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
chmod +x "$STUB/collect-agent-results.sh"
write_voters_three
printf '{"manual_gate_b":true}\n' >"$DBS/run-params.json"
out_bs=$(run_loop "$DBS" 1 --round-cap 2)
printf '%s\n' "$out_bs" | grep -q '^IMPORTANT_ACCEPTED_COUNT=0$' || fail "blank severity should keep IMPORTANT_ACCEPTED_COUNT=0"
if grep -q 'Severity.*important' "$DBS/accepted-plan-findings.md"; then
    fail "blank severity regression unexpectedly promoted blank severity to important"
fi

echo "=== multi-round: validator defects after revise surface plan-validator-defects ==="
DVAL="$TMP/mr-validator"
mkdir -p "$DVAL"
printf 'plan\n\ndiff_lines: 1\n' >"$DVAL/plan.txt"
printf 'feat\n' >"$DVAL/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        *) shift 2 ;;
    esac
done
cp "${CLAUDE_PLUGIN_ROOT:?}/skills/design/scripts/fixtures/validate-plan-commands/demo-plan.md" "$DESIGN_TMPDIR/plan.txt"
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_val=$(run_loop "$DVAL" 1 --round-cap 2 --convergence-threshold 3)
printf '%s\n' "$out_val" | grep -q '^LOOP_STATUS=plan-validator-defects$' || fail "validator defects should surface plan-validator-defects"

echo "=== multi-round: plan-size hard trigger after revise surfaces plan-size-trigger ==="
DSIZE="$TMP/mr-size"
mkdir -p "$DSIZE"
printf 'plan\n\ndiff_lines: 1\n' >"$DSIZE/plan.txt"
printf 'feat\n' >"$DSIZE/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        *) shift 2 ;;
    esac
done
{
    printf '## Plan\n\n'
    awk 'BEGIN { for (i = 1; i <= 805; i++) print "line " i }'
    printf 'diff_lines: 1601\n'
} >"$DESIGN_TMPDIR/plan.txt"
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_size=$(run_loop "$DSIZE" 1 --round-cap 2 --convergence-threshold 3)
printf '%s\n' "$out_size" | grep -q '^LOOP_STATUS=plan-size-trigger$' || fail "plan-size hard trigger should surface plan-size-trigger"

echo "=== snapshot allowlist: raw reviewer output excluded from round-1 ==="
DS="$TMP/snap"
mkdir -p "$DS"
printf 'plan\n\ndiff_lines: 1\n' >"$DS/plan.txt"
printf 'feat\n' >"$DS/feature-description.txt"
printf 'sentinel raw\n' >"$DS/cursor-plan-arch-output.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=ok\n'
exit 0
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_s=$(run_loop "$DS" 1 --round-cap 1)
printf '%s\n' "$out_s" | grep -q '^LOOP_STATUS=cap-hit$' || fail "cap 1 expected cap-hit"
[[ -f "$DS/plan-review/round-1/findings.md" ]] || fail "findings.md should snapshot"
[[ ! -f "$DS/plan-review/round-1/cursor-plan-arch-output.txt" ]] || fail "raw reviewer output must not snapshot"
[[ -f "$DS/plan-review/round-1/findings-classification.tsv" ]] || fail "classification TSV must survive round snapshot"

echo "=== snapshot fails closed on allowlisted symlink source ==="
DSS="$TMP/snap-symlink"
mkdir -p "$DSS"
printf 'plan\n\ndiff_lines: 1\n' >"$DSS/plan.txt"
printf 'feat\n' >"$DSS/feature-description.txt"
ln -s "$DSS/feature-description.txt" "$DSS/plan-voter-slots.ndjson"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
set +e
out_ss=$(run_loop "$DSS" 1 --round-cap 2 --convergence-threshold 0)
rc_ss=$?
set -e
[[ "$rc_ss" -eq 1 ]] || fail "allowlisted symlink source should fail snapshot closed"
printf '%s\n' "$out_ss" | grep -q '^LOOP_STATUS=panel-failed$' || fail "symlink snapshot failure should surface panel-failed"
[[ ! -f "$DSS/plan-review/round-1/plan.txt" ]] || fail "failed snapshot must not preserve copied snapshot artifacts"

echo "=== snapshot failure preserves revise forensics and revision-failed status ==="
DSR="$TMP/snap-revision-status"
mkdir -p "$DSR"
printf 'plan\n\ndiff_lines: 1\n' >"$DSR/plan.txt"
printf 'feat\n' >"$DSR/feature-description.txt"
ln -s "$DSR/feature-description.txt" "$DSR/plan-voter-slots.ndjson"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
mkdir -p "$DSR/plan-review/round-1/revise"
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        *) shift 2 ;;
    esac
done
mkdir -p "$DESIGN_TMPDIR/plan-review/round-1/revise"
printf 'prompt\n' >"$DESIGN_TMPDIR/plan-review/round-1/revise/prompt.txt"
printf 'patch\n' >"$DESIGN_TMPDIR/plan-review/round-1/revise/cursor-candidate.patch"
printf 'REVISE_STATUS=failed-no-patch\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_sr=$(run_loop "$DSR" 1 --round-cap 2)
printf '%s\n' "$out_sr" | grep -q '^LOOP_STATUS=revision-failed$' || fail "snapshot failure should preserve revision-failed status"
printf '%s\n' "$out_sr" | grep -q '^REASON=revision-failed,snapshot-failed$' || fail "snapshot failure should append snapshot-failed reason"
[[ -f "$DSR/plan-review/round-1/revise/prompt.txt" ]] || fail "snapshot failure must preserve revise prompt forensics"
[[ -f "$DSR/plan-review/round-1/revise/cursor-candidate.patch" ]] || fail "snapshot failure must preserve revise patch forensics"

echo "=== snapshot failure preserves terminal cap-hit status ==="
DSC="$TMP/snap-cap-status"
mkdir -p "$DSC"
printf 'plan\n\ndiff_lines: 1\n' >"$DSC/plan.txt"
printf 'feat\n' >"$DSC/feature-description.txt"
ln -s "$DSC/feature-description.txt" "$DSC/plan-voter-slots.ndjson"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_sc=$(run_loop "$DSC" 1 --round-cap 1)
printf '%s\n' "$out_sc" | grep -q '^LOOP_STATUS=cap-hit$' || fail "snapshot failure on terminal round should preserve cap-hit"
printf '%s\n' "$out_sc" | grep -q '^REASON=cap-hit,snapshot-failed$' || fail "terminal cap-hit should append snapshot-failed reason"

echo "=== multi-round: degraded round resets convergence streak and dedup failure does not leak ==="
DDR="$TMP/degraded-reset"
mkdir -p "$DDR"
printf 'plan\n\ndiff_lines: 1\n' >"$DDR/plan.txt"
printf 'feat\n' >"$DDR/feature-description.txt"
write_scout
write_dispatch_round1_degraded_then_ok
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
        printf '%s\n' "in_scope	nit	correctness	src/a	Resettable streak finding	scenario	fix"
    } >"$tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
chmod +x "$STUB/collect-agent-results.sh"
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_ddr=$(run_loop "$DDR" 1 --round-cap 3 --convergence-threshold 3)
printf '%s\n' "$out_ddr" | grep -q '^LOOP_STATUS=converged$' || fail "degraded-then-stable rounds should converge"
printf '%s\n' "$out_ddr" | grep -q '^REASON=streak$' || fail "degraded-reset path should converge via streak"
printf '%s\n' "$out_ddr" | grep -q '^ROUNDS_COMPLETED=3$' || fail "degraded-reset path should require three completed rounds"
grep -q '^DEGRADED_PANEL=1$' "$DDR/plan-review/round-1/round-summary.env" || fail "round 1 should record degraded panel"
grep -q '^DEGRADED_PANEL=0$' "$DDR/plan-review/round-2/round-summary.env" || fail "round 2 should reset degraded panel"
grep -q '^DEGRADED_PANEL=0$' "$DDR/plan-review/round-3/round-summary.env" || fail "stable round 3 should remain non-degraded"
[[ -f "$DDR/plan-review/round-3/findings-classification.tsv" ]] || fail "converged terminal round must keep findings-classification TSV"

echo "=== multi-round: dedup failure degrades only the failing round ==="
DDD="$TMP/dedup-reset"
mkdir -p "$DDD"
printf 'plan\n\ndiff_lines: 1\n' >"$DDD/plan.txt"
printf 'feat\n' >"$DDD/feature-description.txt"
write_scout
write_dispatch_round1_degraded_then_ok
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
        printf '%s\n' "in_scope	nit	correctness	src/a	Dedup reset finding	scenario	fix"
    } >"$tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
chmod +x "$STUB/collect-agent-results.sh"
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
PYWRAP="$TMP/python-wrap"
mkdir -p "$PYWRAP"
REAL_PYTHON="$(command -v python3)"
cat >"$PYWRAP/python3" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == *".plan-review-loop-dedup.py" && -n "${DESIGN_TMPDIR:-}" ]]; then
    state="$DESIGN_TMPDIR/.dedup-fail-count"
    count=0
    if [[ -f "$state" ]]; then
        count=$(cat "$state")
    fi
    count=$((count + 1))
    printf '%s\n' "$count" >"$state"
    if [[ "$count" == "1" ]]; then
        exit 99
    fi
fi
exec "${REAL_PYTHON:?}" "$@"
EOS
chmod +x "$PYWRAP/python3"
out_ddd=$(REAL_PYTHON="$REAL_PYTHON" PATH="$PYWRAP:$PATH" run_loop "$DDD" 1 --round-cap 2 --convergence-threshold 3)
printf '%s\n' "$out_ddd" | grep -q '^LOOP_STATUS=cap-hit$' || fail "dedup-reset path should still finish the cap-limited run"
grep -q '^DEGRADED_PANEL=1$' "$DDD/plan-review/round-1/round-summary.env" || fail "dedup failure should degrade round 1"
grep -q '^DEGRADED_PANEL=0$' "$DDD/plan-review/round-2/round-summary.env" || fail "dedup failure must not leak into round 2"

echo "=== snapshot fails closed on symlinked revise artifact sources ==="
DSREV="$TMP/snap-revise-symlink"
mkdir -p "$DSREV"
printf 'plan\n\ndiff_lines: 1\n' >"$DSREV/plan.txt"
printf 'feat\n' >"$DSREV/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        *) shift 2 ;;
    esac
done
mkdir -p "$DESIGN_TMPDIR/plan-review/round-1/revise"
printf 'prompt\n' >"$DESIGN_TMPDIR/plan-review/round-1/revise/prompt.txt"
ln -sf "$DESIGN_TMPDIR/feature-description.txt" "$DESIGN_TMPDIR/plan-review/round-1/revise/cursor-candidate.patch"
printf 'REVISE_STATUS=failed-no-patch\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
set +e
out_dsrev=$(run_loop "$DSREV" 1 --round-cap 2)
rc_dsrev=$?
set -e
[[ "$rc_dsrev" -eq 0 ]] || fail "symlinked revise artifact should preserve terminal revision-failed exit status"
printf '%s\n' "$out_dsrev" | grep -q '^LOOP_STATUS=revision-failed$' || fail "symlinked revise artifact should preserve revision-failed status"
printf '%s\n' "$out_dsrev" | grep -q '^REASON=revision-failed,snapshot-failed$' || fail "symlinked revise artifact should append snapshot-failed reason"

echo "=== multi-round: two-round nit streak converges via streak ==="
DSTR="$TMP/streak-two-round"
mkdir -p "$DSTR"
printf 'plan\n\ndiff_lines: 1\n' >"$DSTR/plan.txt"
printf 'feat\n' >"$DSTR/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one_nit
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_str=$(run_loop "$DSTR" 1 --round-cap 5 --convergence-threshold 3)
printf '%s\n' "$out_str" | grep -q '^LOOP_STATUS=converged$' || fail "two-round nit streak should converge"
printf '%s\n' "$out_str" | grep -q '^REASON=streak$' || fail "two-round nit streak should use streak reason"
printf '%s\n' "$out_str" | grep -q '^CONVERGENCE_STREAK=2$' || fail "two-round nit streak should reach streak 2"
printf '%s\n' "$out_str" | grep -q '^ROUNDS_COMPLETED=2$' || fail "two-round nit streak should complete two rounds"
grep -q '^CONVERGENCE_STREAK=1$' "$DSTR/plan-review/round-1/round-summary.env" || fail "round 1 should record streak 1"

echo "=== multi-round: accepted-count above threshold resets convergence streak ==="
DATHR="$TMP/streak-above-threshold"
mkdir -p "$DATHR"
printf 'plan\n\ndiff_lines: 1\n' >"$DATHR/plan.txt"
printf 'feat\n' >"$DATHR/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect above_threshold
# Voter stub votes YES for all four findings so ACCEPTED_COUNT=4 (above threshold 3)
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
for f in "$v1" "$v2" "$v3"; do
    printf '%s\n' 'FINDING_1: YES' 'FINDING_2: YES' 'FINDING_3: YES' 'FINDING_4: YES' >"$f"
done
printf '%s\n' "$v1" "$v2" "$v3" >"$vp"
printf 'DISPATCH_OK=true\nVOTER_PATHS_FILE=%s\nVOTER_1_PARSE_RATE_STATUS=ok\n' "$vp"
printf 'VOTER_1_PATH=%s\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\n' "$v1"
printf 'VOTER_2_PATH=%s\nVOTER_2_TOOL=codex\nVOTER_2_STATUS=launched\n' "$v2"
printf 'VOTER_3_PATH=%s\nVOTER_3_TOOL=cursor\nVOTER_3_STATUS=launched\n' "$v3"
EOS
chmod +x "$STUB/dispatch-plan-voters.sh"
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
run_loop "$DATHR" 1 --round-cap 5 --convergence-threshold 3 >/dev/null
grep -q '^CONVERGENCE_STREAK=0$' "$DATHR/plan-review/round-1/round-summary.env" || fail "above-threshold round 1 should keep streak at 0"
grep -q '^ACCEPTED_COUNT=4$' "$DATHR/plan-review/round-1/round-summary.env" || fail "above-threshold round 1 should record 4 accepted findings"

echo "=== multi-round: important finding resets convergence streak ==="
DIRS="$TMP/streak-important-reset"
mkdir -p "$DIRS"
printf 'plan\n\ndiff_lines: 1\n' >"$DIRS/plan.txt"
printf 'feat\n' >"$DIRS/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect_important_round2
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_irs=$(run_loop "$DIRS" 1 --round-cap 5 --convergence-threshold 3)
printf '%s\n' "$out_irs" | grep -q '^LOOP_STATUS=converged$' || fail "important-reset path should converge"
printf '%s\n' "$out_irs" | grep -q '^REASON=streak$' || fail "important-reset path should use streak reason"
printf '%s\n' "$out_irs" | grep -q '^IMPORTANT_ACCEPTED_COUNT=0$' || fail "important-reset path should finish with IMPORTANT_ACCEPTED_COUNT=0"
printf '%s\n' "$out_irs" | grep -q '^CONVERGENCE_STREAK=2$' || fail "important-reset path should finish at streak 2"
printf '%s\n' "$out_irs" | grep -q '^ROUNDS_COMPLETED=4$' || fail "important-reset path should complete four rounds"
grep -q '^IMPORTANT_ACCEPTED_COUNT=0$' "$DIRS/.step3-plan-review-result.env" || fail "terminal result env should record IMPORTANT_ACCEPTED_COUNT=0"
grep -q '^IMPORTANT_ACCEPTED_COUNT=0$' "$DIRS/plan-review/round-1/round-summary.env" || fail "round 1 should record IMPORTANT_ACCEPTED_COUNT=0"
grep -q '^IMPORTANT_ACCEPTED_COUNT=1$' "$DIRS/plan-review/round-2/round-summary.env" || fail "round 2 should record IMPORTANT_ACCEPTED_COUNT=1"
grep -q '^IMPORTANT_ACCEPTED_COUNT=0$' "$DIRS/plan-review/round-3/round-summary.env" || fail "round 3 should record IMPORTANT_ACCEPTED_COUNT=0"
grep -q '^IMPORTANT_ACCEPTED_COUNT=0$' "$DIRS/plan-review/round-4/round-summary.env" || fail "round 4 should record IMPORTANT_ACCEPTED_COUNT=0"
grep -q '^CONVERGENCE_STREAK=1$' "$DIRS/plan-review/round-1/round-summary.env" || fail "round 1 should advance streak to 1"
grep -q '^CONVERGENCE_STREAK=0$' "$DIRS/plan-review/round-2/round-summary.env" || fail "round 2 important finding should reset streak to 0"
grep -q '^CONVERGENCE_STREAK=1$' "$DIRS/plan-review/round-3/round-summary.env" || fail "round 3 should rebuild streak to 1"

echo "=== multi-round: degraded round 2 resets convergence streak (dedicated) ==="
DDR2="$TMP/streak-degraded-round2"
mkdir -p "$DDR2"
printf 'plan\n\ndiff_lines: 1\n' >"$DDR2/plan.txt"
printf 'feat\n' >"$DDR2/feature-description.txt"
write_scout
write_dispatch_round2_degraded
write_collect one_nit
write_voters_three
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
out_ddr2=$(run_loop "$DDR2" 1 --round-cap 5 --convergence-threshold 3)
printf '%s\n' "$out_ddr2" | grep -q '^LOOP_STATUS=converged$' || fail "degraded-round2 path should converge"
printf '%s\n' "$out_ddr2" | grep -q '^REASON=streak$' || fail "degraded-round2 path should use streak reason"
printf '%s\n' "$out_ddr2" | grep -q '^CONVERGENCE_STREAK=2$' || fail "degraded-round2 path should finish at streak 2"
printf '%s\n' "$out_ddr2" | grep -q '^ROUNDS_COMPLETED=4$' || fail "degraded-round2 path should complete four rounds"
grep -q '^CONVERGENCE_STREAK=1$' "$DDR2/plan-review/round-1/round-summary.env" || fail "round 1 should advance streak to 1"
grep -q '^CONVERGENCE_STREAK=0$' "$DDR2/plan-review/round-2/round-summary.env" || fail "round 2 degraded panel should reset streak to 0"
grep -q '^DEGRADED_PANEL=1$' "$DDR2/plan-review/round-2/round-summary.env" || fail "round 2 should record degraded panel"

echo "=== post-apply: section-aware duplicate-line dedup ==="
DDED="$TMP/section-aware-dedup"
mkdir -p "$DDED"
cat >"$DDED/plan.txt" <<'PLAN'
## Intro

duplicate outside
duplicate outside

## Constraints

duplicate inside constraints
duplicate inside constraints

### Hard constraints

duplicate nested
duplicate nested

```
## Constraints lookalike
duplicate fenced
duplicate fenced
```

```bash
## Constraints
duplicate tagged fenced
duplicate tagged fenced
```

## Constraints-related notes

duplicate lookalike
duplicate lookalike

## After

diff_lines: 1
PLAN
cat >"$STUB/dedup-emit-driver.sh" <<'EOS'
#!/usr/bin/env bash
printf 'EMIT_PLAN_STATUS=ok\n'
EOS
chmod +x "$STUB/dedup-emit-driver.sh"
cat >"$STUB/dedup-validate.sh" <<'EOS'
#!/usr/bin/env bash
printf 'VALIDATE_STATUS=ok\n'
EOS
chmod +x "$STUB/dedup-validate.sh"
export DESIGN_TMPDIR="$DDED"
export CLAUDE_PLUGIN_ROOT="$ROOT"
export DESIGN_DRIVER_SH="$STUB/dedup-emit-driver.sh"
export INVOKE_PLAN_VALIDATOR_SH="$STUB/dedup-validate.sh"
export CHECK_PLAN_SIZE_SH="$ROOT/skills/design/scripts/check-plan-size.sh"
export LARCH_QUIET_DISABLE=1
# shellcheck disable=SC1091
source "$ROOT/scripts/lib-quiet.sh"
larch_quiet_init
dedup_log=$(
    bash -c '
        set -euo pipefail
        # shellcheck disable=SC1091
        source "$1/scripts/lib-quiet.sh"
        larch_quiet_init
        export DESIGN_TMPDIR DESIGN_DRIVER_SH INVOKE_PLAN_VALIDATOR_SH CHECK_PLAN_SIZE_SH CLAUDE_PLUGIN_ROOT
        eval "$(awk "/^_run_post_apply_pipeline\\(\\)/,/^}$/" "$2")"
        _run_post_apply_pipeline 1
    ' _ "$ROOT" "$PLR" 2>&1
)
printf '%s\n' "$dedup_log" | grep -q 'dedup-sweep: removed 4 duplicate line(s) from plan.txt' || fail "section-aware dedup should remove four duplicates"
outside_count=$(grep -c '^duplicate outside$' "$DDED/plan.txt" || true)
inside_count=$(grep -c '^duplicate inside constraints$' "$DDED/plan.txt" || true)
lookalike_count=$(grep -c '^duplicate lookalike$' "$DDED/plan.txt" || true)
nested_count=$(grep -c '^duplicate nested$' "$DDED/plan.txt" || true)
fenced_count=$(grep -c '^duplicate fenced$' "$DDED/plan.txt" || true)
tagged_fenced_count=$(grep -c '^duplicate tagged fenced$' "$DDED/plan.txt" || true)
[[ "$outside_count" == "1" ]] || fail "outside Constraints duplicates should collapse"
[[ "$inside_count" == "2" ]] || fail "inside Constraints duplicates should be preserved"
[[ "$lookalike_count" == "1" ]] || fail "Constraints-prefixed non-Constraints heading should not be protected"
[[ "$nested_count" == "2" ]] || fail "nested Constraints duplicates should be preserved"
[[ "$fenced_count" == "1" ]] || fail "fenced duplicates should collapse"
[[ "$tagged_fenced_count" == "1" ]] || fail "language-tagged fenced duplicates should collapse"

printf '%s\n' "test-plan-review-loop: ok"
