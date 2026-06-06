#!/usr/bin/env bash
# Offline harness for scripts/lib-scope-anchor-handoff.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
# shellcheck source=scripts/lib-scope-anchor-handoff.sh
source "$ROOT/scripts/lib-scope-anchor-handoff.sh"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-lib-scope-anchor-handoff.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
DESIGN_CANON="$(cd "$TMP" && pwd -P)"
printf 'anchor body\n' >"$TMP/plan-review-scope-anchor.txt"
printf 'alt anchor\n' >"$TMP/plan-review-scope-anchor-alt.txt"

TALLY_PLAN_REVIEW_STATUS=ok
LOOP_STATUS=complete
out=$(larch_scope_anchor_retally_handoff_value "$DESIGN_CANON" "$TMP/plan-review-scope-anchor-alt.txt" "$TMP/plan-review-scope-anchor.txt")
[[ "$out" == "$DESIGN_CANON/plan-review-scope-anchor-alt.txt" ]] \
    || fail 'parsed re-tally anchor should win over input fallback'

TALLY_PLAN_REVIEW_STATUS=ok
LOOP_STATUS=complete
out=$(larch_scope_anchor_retally_handoff_value "$DESIGN_CANON" "" "$TMP/plan-review-scope-anchor.txt")
[[ "$out" == "$DESIGN_CANON/plan-review-scope-anchor.txt" ]] \
    || fail 're-tally should fall back to input anchor on ok when stdout omits KV'

TALLY_PLAN_REVIEW_STATUS=tally-error
LOOP_STATUS=complete
out=$(larch_scope_anchor_retally_handoff_value "$DESIGN_CANON" "" "$TMP/plan-review-scope-anchor.txt")
[[ -z "$out" ]] || fail 're-tally must omit anchor on tally-error even with stale input'

TALLY_PLAN_REVIEW_STATUS=ok
LOOP_STATUS=complete
out=$(larch_scope_anchor_retally_handoff_value "$DESIGN_CANON" $'/tmp/evil\ranchor.txt' "$TMP/plan-review-scope-anchor.txt")
[[ "$out" == "$DESIGN_CANON/plan-review-scope-anchor.txt" ]] \
    || fail 'CR/LF-parsed re-tally anchor must be rejected; input fallback allowed on ok'

TALLY_PLAN_REVIEW_STATUS=ok
LOOP_STATUS=panel-failed
out=$(larch_scope_anchor_design_handoff_value "$DESIGN_CANON" "$TMP/plan-review-scope-anchor.txt" "$TMP/plan-review-scope-anchor-alt.txt")
[[ -z "$out" ]] || fail 'panel-failed LOOP_STATUS must omit scope anchor handoff'

TALLY_PLAN_REVIEW_STATUS=tally-error
LOOP_STATUS=panel-failed
out=$(larch_scope_anchor_design_handoff_value "$DESIGN_CANON" "$TMP/plan-review-scope-anchor.txt")
[[ -z "$out" ]] || fail 'panel-failed with tally-error must omit scope anchor handoff'

pass 'lib-scope-anchor-handoff harness'
