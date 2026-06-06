#!/usr/bin/env bash
# Cross-script integration: plan-review-loop single-pass output vs round artifact staging.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
PLR="$ROOT/skills/design/scripts/plan-review-loop.sh"
fail() { printf '%s\n' "$1" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-design-single-pass-int.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
STUB="$TMP/stub-bin"
mkdir -p "$STUB" "$TMP/design"

cat >"$STUB/scout-plan-archetypes-wrapper.sh" <<'EOS'
#!/usr/bin/env bash
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in --output) out="${2:?}"; shift 2 ;; *) shift 1 ;; esac
done
printf '%s\n' '{"archetypes":[]}' >"$out"
EOS
chmod +x "$STUB/scout-plan-archetypes-wrapper.sh"

cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;; *) shift 1 ;; esac
done
OUT="$DESIGN_TMPDIR/cursor-plan-arch-output.txt"
printf '%s\n' '{"slot":"cursor-plan-arch","tool":"cursor","output":"'"$OUT"'"}' >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
: >"$OUT"
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
printf '%s\n' "$OUT" >"$PATHS"
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nCOMBINED_FALLBACK_COUNT=0\nSTATIC_DISPATCH_OK=true\nPANEL_PATHS_FILE=%s\n' "$PATHS"
EOS
chmod +x "$STUB/dispatch-plan-review-panel.sh"

cat >"$STUB/collect-agent-results.sh" <<'EOS'
#!/usr/bin/env bash
paths=""
while [[ $# -gt 0 ]]; do
    case "$1" in --paths-file) paths="${2:?}"; shift 2 ;; *) shift 1 ;; esac
done
while IFS= read -r p; do
    [[ -z "$p" ]] && continue
    tsv="${p}.tsv"
    {
        printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix"
        printf '%s\n' "in_scope	nit	correctness	src/a	Single pass finding	scenario	fix"
        printf '%s\n' "out_of_scope	important	correctness	src/o	Accepted OOS	scenario	fix"
    } >"$tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
chmod +x "$STUB/collect-agent-results.sh"

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

out=$(env -u LARCH_QUIET_PID \
    CLAUDE_PLUGIN_ROOT="$ROOT" \
    LARCH_QUIET_DISABLE=1 \
    LARCH_PLAN_REVIEW_SCOUT_SH="$STUB/scout-plan-archetypes-wrapper.sh" \
    LARCH_PLAN_REVIEW_DISPATCH_PANEL_SH="$STUB/dispatch-plan-review-panel.sh" \
    LARCH_PLAN_REVIEW_COLLECT_SH="$STUB/collect-agent-results.sh" \
    LARCH_PLAN_REVIEW_DISPATCH_VOTERS_SH="$STUB/dispatch-plan-voters.sh" \
    LARCH_AGGREGATOR_DISABLED=1 \
    bash "$PLR" \
        --design-tmpdir "$TMP/design" \
        --plan-file "$TMP/design/plan.txt" \
        --feature-file "$TMP/design/feature-description.txt" \
        --codex-present true \
        --cursor-present true \
        --round-num 1 \
        --round-cap 3)

printf '%s\n' "$out" | grep -q '^LOOP_STATUS=complete$' || fail "expected complete from single-pass integration loop"
printf '%s\n' "$out" | grep -q '^REVISE_STATUS=skipped$' || fail "single-pass loop must not auto-revise"
printf '%s\n' "$out" | grep -q '^ROUNDS_COMPLETED=1$' || fail "single-pass loop should complete exactly one round"
[[ -d "$TMP/design/plan-review/round-1" ]] || fail "round-1 missing"
[[ ! -d "$TMP/design/plan-review/round-2" ]] || fail "round-2 must not be created by single-pass loop"
[[ ! -d "$TMP/design/plan-review/round-1/revise" ]] || fail "single-pass loop must not write revise artifacts"
grep -q '^LOOP_STATUS=complete$' "$TMP/design/plan-review/round-1/round-summary.env" || fail "round summary should record complete"
grep -q '^REVISE_STATUS=skipped$' "$TMP/design/plan-review/round-1/round-summary.env" || fail "round summary should record skipped revise"
grep -q 'Accepted OOS' "$TMP/design/oos-accepted-design.md" || fail "accepted OOS should accumulate"
[[ -f "$TMP/design/plan-review/round-1/findings-classification.tsv" ]] || fail "classification TSV missing"
[[ -f "$TMP/design/.step3-plan-review-result.env" ]] || fail "result env missing"

printf '%s\n' 'test-design-multi-round-integration: ok'
