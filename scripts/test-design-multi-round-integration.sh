#!/usr/bin/env bash
# Cross-script integration: plan-review-loop multi-round output vs design-log-publish staging.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
PLR="$ROOT/skills/design/scripts/plan-review-loop.sh"

fail() { printf '%s\n' "$1" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-design-mr-int.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
STUB="$TMP/stub-bin"
mkdir -p "$STUB" "$TMP/design" "$TMP/stage"

printf '## Plan\n\nDo thing.\n\ndiff_lines: 3\n' >"$TMP/design/plan.txt"
printf 'feat\n' >"$TMP/design/feature-description.txt"

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
    case "$1" in --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;; *) shift 2 ;; esac
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
    printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix" >"$tsv"
    printf '%s\n' "in_scope	nit	correctness	src/a	concern text here	scenario	fix" >>"$tsv"
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
v="$DESIGN_TMPDIR/v1.txt"
printf 'FINDING_1: YES\n' >"$v"
printf 'DISPATCH_OK=true\nVOTER_1_PATH=%s\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\n' "$v"
EOS
chmod +x "$STUB/dispatch-plan-voters.sh"

cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;; *) shift 2 ;; esac
done
mkdir -p "$DESIGN_TMPDIR/plan-review/round-1/revise"
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n' >"$DESIGN_TMPDIR/plan-review/round-1/revise/revise.env"
printf 'patch\n' >"$DESIGN_TMPDIR/plan-review/round-1/revise/patch.diff"
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
exit 0
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"

export CLAUDE_PLUGIN_ROOT="$ROOT"
export LARCH_QUIET_DISABLE=1
export LARCH_PLAN_REVIEW_SCOUT_SH="$STUB/scout-plan-archetypes-wrapper.sh"
export LARCH_PLAN_REVIEW_DISPATCH_PANEL_SH="$STUB/dispatch-plan-review-panel.sh"
export LARCH_PLAN_REVIEW_COLLECT_SH="$STUB/collect-agent-results.sh"
export LARCH_PLAN_REVIEW_DISPATCH_VOTERS_SH="$STUB/dispatch-plan-voters.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
export LARCH_AGGREGATOR_DISABLED=1

out=$(bash "$PLR" \
    --design-tmpdir "$TMP/design" \
    --plan-file "$TMP/design/plan.txt" \
    --feature-file "$TMP/design/feature-description.txt" \
    --codex-present true \
    --cursor-present true \
    --round-cap 2 \
    --convergence-threshold 3)
printf '%s\n' "$out" | grep -q '^LOOP_STATUS=cap-hit$' || fail "expected cap-hit from integration loop"

[[ -d "$TMP/design/plan-review/round-1" ]] || fail "round-1 missing"
[[ -f "$TMP/design/plan-review/round-1/round-summary.env" ]] || fail "round-summary missing"

# shellcheck source=scripts/lib-design-round-artifacts.sh
source "$ROOT/scripts/lib-design-round-artifacts.sh"
design_round_artifact_included unknown.bin && fail "unknown.bin must be excluded by allowlist"
design_round_artifact_included findings.md || fail "findings.md must be included"
design_round_revise_artifact_included patch.diff || fail "patch.diff must be included in revise/"
design_round_revise_artifact_included extra.log && fail "extra.log must be excluded from revise/"

# Raw reviewer output at session root must not appear in round snapshot.
[[ ! -f "$TMP/design/plan-review/round-1/cursor-plan-arch-output.txt" ]] || fail "raw reviewer output must not snapshot"

printf '%s\n' 'test-design-multi-round-integration: ok'
