#!/usr/bin/env bash
# Cross-script integration: per-entry plan-review output and automatic multi-round staging.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
CLI="$ROOT/python/cli.py"
fail() { printf '%s\n' "$1" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-design-multi-round-int.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
STUB="$TMP/stub-bin"
mkdir -p "$STUB" "$TMP/design"

cat >"$STUB/scout-plan-archetypes-cli" <<'EOS'
#!/usr/bin/env bash
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in --output) out="${2:?}"; shift 2 ;; *) shift 1 ;; esac
done
printf '%s\n' '{"archetypes":[]}' >"$out"
EOS
chmod +x "$STUB/scout-plan-archetypes-cli"

cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;; *) shift 1 ;; esac
done
OUT="$DESIGN_TMPDIR/cursor-plan-arch-output.txt"
printf '%s\n' '{"slot":"cursor-plan-arch","tool":"cursor","output":"'"$OUT"'"}' >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
printf '%s
' "NO_ISSUES_FOUND" >"$OUT"
tsv="${OUT}.tsv"
{
    printf '%s
' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix"
    printf '%s
' "in_scope	nit	correctness	src/a	Single pass finding	scenario	fix"
    printf '%s
' "out_of_scope	important	correctness	src/o	Accepted OOS	scenario	fix"
} >"$tsv"
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
printf '%s\n' "$OUT" >"$PATHS"
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nCOMBINED_FALLBACK_COUNT=0\nSTATIC_DISPATCH_OK=true\nPANEL_PATHS_FILE=%s\n' "$PATHS"
EOS
chmod +x "$STUB/dispatch-plan-review-panel.sh"

mkdir -p "$STUB/python"
cat >"$STUB/python/cli.py" <<'EOS'
#!/usr/bin/env bash
if [[ "${1:-}" != "agent" || "${2:-}" != "collect-results" ]]; then
    printf 'unexpected stub cli invocation: %s
' "$*" >&2
    exit 2
fi
shift 2
paths=""
while [[ $# -gt 0 ]]; do
    case "$1" in --paths-file) paths="${2:?}"; shift 2 ;; *) shift 1 ;; esac
done
while IFS= read -r p; do
    [[ -z "$p" ]] && continue
    tsv="${p}.tsv"
    {
        printf '%s
' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix"
        printf '%s
' "in_scope	nit	correctness	src/a	Single pass finding	scenario	fix"
        printf '%s
' "out_of_scope	important	correctness	src/o	Accepted OOS	scenario	fix"
    } >"$tsv"
    printf 'REVIEWER_FILE=%s
TOOL=cursor
STATUS=OK
EXIT_CODE=0

' "$p"
done <"$paths"
EOS
chmod +x "$STUB/python/cli.py"

cat >"$STUB/dispatch-plan-voters.sh" <<'EOS'
#!/usr/bin/env bash
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;; *) shift 1 ;; esac
done
v1="$DESIGN_TMPDIR/v1.txt"
v2="$DESIGN_TMPDIR/v2.txt"
printf 'FINDING_1: YES\nOOS_1: YES\n' >"$v1"
printf 'FINDING_1: YES\nOOS_1: YES\n' >"$v2"
printf 'DISPATCH_OK=true\nVOTER_1_PATH=%s\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\nVOTER_2_PATH=%s\nVOTER_2_TOOL=codex\nVOTER_2_STATUS=launched\n' "$v1" "$v2"
EOS
chmod +x "$STUB/dispatch-plan-voters.sh"

printf '## Plan\n\nDo thing.\n\ndiff_lines: 3\n' >"$TMP/design/plan.txt"
printf 'feat\n' >"$TMP/design/feature-description.txt"

per_entry_stub="$TMP/per-entry-plan-review-loop.sh"
cat >"$per_entry_stub" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
design=""
while [[ $# -gt 0 ]]; do
    case "$1" in --design-tmpdir) design="${2:?}"; shift 2 ;; *) shift ;; esac
done
round_dir="${design}/plan-review/round-1"
mkdir -p "$round_dir"
printf 'LOOP_STATUS=complete\nREVISE_STATUS=skipped\n' >"$round_dir/round-summary.env"
{
    printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix"
    printf '%s\n' "out_of_scope	important	correctness	src/o	Accepted OOS	scenario	fix"
} >"$round_dir/findings-classification.tsv"
printf '## Accepted OOS\n\nAccepted OOS finding\n' >"${design}/oos-accepted-design.md"
cat >"${design}/.step3-plan-review-result.env" <<'ENV'
LOOP_STATUS=complete
ACCEPTED_COUNT=0
IMPORTANT_ACCEPTED_COUNT=0
DEGRADED_PANEL=0
ROUNDS_COMPLETED=1
TALLY_PLAN_REVIEW_STATUS=ok
AGGREGATOR_STATUS=ok
VOTING_TALLY_FILE=
ENV
printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'
EOS
chmod +x "$per_entry_stub"

out=$(env -u LARCH_QUIET_PID \
    CLAUDE_PLUGIN_ROOT="$ROOT" \
    LARCH_QUIET_DISABLE=1 \
    LARCH_AGGREGATOR_DISABLED=1 \
    RUN_STEP3_PLAN_REVIEW_LOOP_SH="$per_entry_stub" \
    python3 "$CLI" plan-review run \
        --design-tmpdir "$TMP/design" \
        --no-preview
        )

if ! printf '%s\n' "$out" | grep -q '^LOOP_STATUS=complete$'; then
    fail "expected complete from per-entry integration loop"
fi
printf '%s\n' "$out" | grep -q '^ROUNDS_COMPLETED=1$' || fail "per-entry loop should complete exactly one round"
[[ -d "$TMP/design/plan-review/round-1" ]] || fail "round-1 missing"
[[ ! -d "$TMP/design/plan-review/round-2" ]] || fail "round-2 must not be created by the first per-entry loop"
[[ ! -d "$TMP/design/plan-review/round-1/revise" ]] || fail "per-entry loop must not write revise artifacts"
grep -q '^LOOP_STATUS=complete$' "$TMP/design/plan-review/round-1/round-summary.env" || fail "round summary should record complete"
grep -q '^REVISE_STATUS=skipped$' "$TMP/design/plan-review/round-1/round-summary.env" || fail "round summary should record skipped revise"
grep -q 'Accepted OOS' "$TMP/design/oos-accepted-design.md" || fail "accepted OOS should accumulate"
[[ -f "$TMP/design/plan-review/round-1/findings-classification.tsv" ]] || fail "classification TSV missing"
[[ -f "$TMP/design/.step3-plan-review-result.env" ]] || fail "result env missing"

D2="$TMP/design-chain"
mkdir -p "$D2"
cat >"$D2/run-params.json" <<'EOF'
{"schema_version":3,"approve_requested":false,"partition_requested":false,"brainstorm_requested":false}
EOF
printf '## Plan\n\nDo thing better.\n\ndiff_lines: 3\n' >"$D2/plan.txt"
printf 'feat\n' >"$D2/feature-description.txt"
chain_stub="$TMP/chain-plan-review-loop.sh"
cat >"$chain_stub" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
round_num=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --round-num) round_num="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
mkdir -p "${DESIGN_TMPDIR:?}/plan-review/round-${round_num}"
if [[ "$round_num" == 2 && -e "${DESIGN_TMPDIR}/.step3-review-result.env" ]]; then
    printf 'round 2 saw stale .step3-review-result.env\n' >&2
    exit 70
fi
printf 'artifact for round %s\n' "$round_num" >"${DESIGN_TMPDIR}/plan-review/round-${round_num}/artifact.txt"
if [[ "$round_num" == 1 ]]; then
    cat >"${DESIGN_TMPDIR}/accepted-plan-findings.md" <<'FINDINGS'
### FINDING_1: Important continuation
- **Severity**: important
- **Concern**: important issue after Gate B
FINDINGS
fi
printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=1\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=%s\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n' "$round_num"
EOS
chmod +x "$chain_stub"
for helper in revise-ok.sh dedup-ok.sh postplan-ok.sh continue-true.sh; do
    case "$helper" in
        revise-ok.sh) cat >"$D2/$helper" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
plan=""
while [[ $# -gt 0 ]]; do case "$1" in --plan-file) plan="${2:?}"; shift 2 ;; *) shift ;; esac; done
printf '\n# revised\n' >>"$plan"
printf 'REVISE_STATUS=ok\n'
STUB
        ;;
        dedup-ok.sh) cat >"$D2/$helper" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
exit 0
STUB
        ;;
        postplan-ok.sh) cat >"$D2/$helper" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
dir=""
while [[ $# -gt 0 ]]; do case "$1" in --design-tmpdir) dir="${2:?}"; shift 2 ;; *) shift ;; esac; done
printf 'POSTPLAN_EMIT_STATUS=ok\n' >"$dir/.design-postplan-emit-result.env"
exit 0
STUB
        ;;
        continue-true.sh) cat >"$D2/$helper" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
round_file="${DESIGN_TMPDIR:?}/review-round-count.txt"
round=1
[[ -s "$round_file" ]] && round="$(tr -d '[:space:]' <"$round_file")"
if [[ "$round" == 1 ]]; then
  printf 'PLAN_REVIEW_CONTINUE=true\nPLAN_REVIEW_CONTINUE_REASON=high-accepted\nACCEPTED_COUNT=1\nDEGRADED_PANEL=0\n'
else
  printf 'PLAN_REVIEW_CONTINUE=false\nPLAN_REVIEW_CONTINUE_REASON=small-clean\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\n'
fi
STUB
        ;;
    esac
    chmod +x "$D2/$helper"
done

run_step3_out=$(env -u LARCH_QUIET_PID \
    CLAUDE_PLUGIN_ROOT="$ROOT" \
    RUN_STEP3_PLAN_REVIEW_LOOP_SH="$chain_stub" \
    RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH="$D2/revise-ok.sh" \
    RUN_STEP3_DEDUP_PLAN_SH="$D2/dedup-ok.sh" \
    RUN_STEP3_POSTPLAN_EMIT_SH="$D2/postplan-ok.sh" \
    RUN_STEP3_CONTINUATION_SH="$D2/continue-true.sh" \
    python3 "$CLI" plan-review run --design-tmpdir "$D2" --mode loop)
printf '%s\n' "$run_step3_out" | grep -q '^STEP3_REVIEW_LOOP_STATUS=complete$' || fail "loop mode should finish with complete envelope"
printf '%s\n' "$run_step3_out" | grep -q '^FINAL_ROUND_NUM=2$' || fail "loop mode should complete two review rounds"
printf 'preserve me\n' >"$D2/plan-review/round-1/preserve.txt"
[[ -f "$D2/plan-review/round-1/preserve.txt" ]] || fail "round-1 artifact should survive automatic round-2 entry"
[[ -f "$D2/plan-review/round-2/artifact.txt" ]] || fail "round-2 artifact should be written"
[[ -f "$D2/.completed/step-3" ]] || fail "loop terminal path should write step-3"
[[ -f "$D2/.completed/step-3.5" ]] || fail "loop terminal path should write step-3.5"
grep -q '^STEP3_REVIEW_LOOP_STATUS=complete$' "$D2/.step3-review-result.env" || fail "loop envelope should persist to result env"

printf '%s\n' 'test-design-multi-round-integration: ok'
