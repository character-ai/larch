#!/usr/bin/env bash
# Regression harness for scripts/write-run-params.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
WRITER="$REPO_ROOT/scripts/write-run-params.sh"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-run-params-test.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

OUT="$TMPROOT/run-params.json"
# shellcheck disable=SC2016 # literal shell-shaped payload; writer must JSON-escape it as data.
reason='quote " newline
$(not executed)'

"$WRITER" \
    --classification SIMPLE \
    --reason "$reason" \
    --source caller-forwarded \
    --sketch-budget 2 \
    --review-budget quick \
    --workflow-path SIMPLE \
    --output "$OUT" >/dev/null

[[ -s "$OUT" ]] || fail "writer did not create run-params.json"
jq -e '
  .schema_version == 1 and
  .design_classification == "SIMPLE" and
  .design_classification_reason == $reason and
  .design_classification_source == "caller-forwarded" and
  .sketch_budget == 2 and
  .review_budget == "quick" and
  .workflow_path == "SIMPLE" and
  .partition_requested == false and
  .brainstorm_requested == false and
  .manual_gate_b == false
' --arg reason "$reason" "$OUT" >/dev/null || fail "valid JSON did not match expected schema"

if "$WRITER" \
    --classification MEDIUM \
    --reason bad \
    --source caller-forwarded \
    --sketch-budget 2 \
    --review-budget quick \
    --workflow-path SIMPLE \
    --output "$TMPROOT/invalid-classification.json" >/dev/null 2>&1; then
    fail "invalid classification was accepted"
fi

if "$WRITER" \
    --classification SIMPLE \
    --reason bad \
    --source caller-forwarded \
    --sketch-budget 3 \
    --review-budget quick \
    --workflow-path SIMPLE \
    --output "$TMPROOT/invalid-budget.json" >/dev/null 2>&1; then
    fail "invalid sketch budget was accepted"
fi

if ( cd "$TMPROOT" && "$WRITER" \
    --classification HARD \
    --reason bad \
    --source caller-forwarded \
    --sketch-budget 4 \
    --review-budget full \
    --workflow-path HARD \
    --output relative.json >/dev/null 2>&1 ); then
    fail "relative output path was accepted"
fi

"$WRITER" \
    --classification HARD \
    --reason "full overrides quick sketch cap" \
    --source caller-forwarded \
    --sketch-budget 4 \
    --review-budget quick \
    --workflow-path HARD \
    --output "$TMPROOT/full-plus-quick.json" >/dev/null
jq -e '.sketch_budget == 4 and .review_budget == "quick"' "$TMPROOT/full-plus-quick.json" >/dev/null \
    || fail "--full + --quick budget example was not represented"

"$WRITER" \
    --classification TRIVIAL_DOC_ONLY \
    --reason "doc-only scan confirmed" \
    --source caller-forwarded \
    --sketch-budget 0 \
    --review-budget full \
    --workflow-path SIMPLE \
    --output "$TMPROOT/trivial.json" >/dev/null
jq -e '
  .design_classification == "TRIVIAL_DOC_ONLY" and
  .design_classification_source == "caller-forwarded" and
  .workflow_path == "SIMPLE" and
  .sketch_budget == 0 and
  .partition_requested == false and
  .brainstorm_requested == false and
  .manual_gate_b == false
' "$TMPROOT/trivial.json" >/dev/null \
    || fail "trivial preset JSON did not match expected classification fields"

if "$WRITER" \
    --classification SIMPLE \
    --reason bad \
    --source caller-forwarded \
    --sketch-budget 2 \
    --review-budget quick \
    --workflow-path SIMPLE \
    --partition-requested maybe \
    --output "$TMPROOT/bad-partition.json" >/dev/null 2>&1; then
    fail "invalid partition-requested was accepted"
fi

if "$WRITER" \
    --classification SIMPLE \
    --reason bad \
    --source caller-forwarded \
    --sketch-budget 2 \
    --review-budget quick \
    --workflow-path SIMPLE \
    --brainstorm-requested maybe \
    --output "$TMPROOT/bad-brainstorm.json" >/dev/null 2>&1; then
    fail "invalid brainstorm-requested was accepted"
fi

if "$WRITER" \
    --classification SIMPLE \
    --reason bad \
    --source caller-forwarded \
    --sketch-budget 2 \
    --review-budget quick \
    --workflow-path SIMPLE \
    --manual-gate-b maybe \
    --output "$TMPROOT/bad-manual-gate-b.json" >/dev/null 2>&1; then
    fail "invalid manual-gate-b was accepted"
fi

if "$WRITER" \
    --classification SIMPLE \
    --reason bad \
    --source router-pre-design \
    --sketch-budget 2 \
    --review-budget quick \
    --workflow-path SIMPLE \
    --output "$TMPROOT/bad-source.json" >/dev/null 2>&1; then
    fail "obsolete --source router-pre-design was accepted"
fi

"$WRITER" \
    --classification SIMPLE \
    --reason "partition flag on" \
    --source caller-forwarded \
    --sketch-budget 2 \
    --review-budget quick \
    --workflow-path SIMPLE \
    --partition-requested true \
    --output "$TMPROOT/partition-true.json" >/dev/null
jq -e '.partition_requested == true' "$TMPROOT/partition-true.json" >/dev/null \
    || fail "--partition-requested true did not set JSON true"

"$WRITER" \
    --classification SIMPLE \
    --reason "brainstorm flag on" \
    --source caller-forwarded \
    --sketch-budget 2 \
    --review-budget quick \
    --workflow-path SIMPLE \
    --brainstorm-requested true \
    --output "$TMPROOT/brainstorm-true.json" >/dev/null
jq -e '.brainstorm_requested == true' "$TMPROOT/brainstorm-true.json" >/dev/null \
    || fail "--brainstorm-requested true did not set JSON true"

"$WRITER" \
    --classification SIMPLE \
    --reason "manual Gate B on" \
    --source caller-forwarded \
    --sketch-budget 2 \
    --review-budget quick \
    --workflow-path SIMPLE \
    --manual-gate-b true \
    --output "$TMPROOT/manual-gate-b-true.json" >/dev/null
jq -e '.manual_gate_b == true' "$TMPROOT/manual-gate-b-true.json" >/dev/null \
    || fail "--manual-gate-b true did not set JSON true"

"$WRITER" \
    --classification SIMPLE \
    --reason "manual Gate B off" \
    --source caller-forwarded \
    --sketch-budget 2 \
    --review-budget quick \
    --workflow-path SIMPLE \
    --manual-gate-b false \
    --output "$TMPROOT/manual-gate-b-false.json" >/dev/null
jq -e '.manual_gate_b == false' "$TMPROOT/manual-gate-b-false.json" >/dev/null \
    || fail "--manual-gate-b false did not set JSON false"

"$WRITER" \
    --classification SIMPLE \
    --reason "FINDING_15 all flags" \
    --source caller-forwarded \
    --sketch-budget 2 \
    --review-budget quick \
    --workflow-path SIMPLE \
    --partition-requested true \
    --brainstorm-requested true \
    --manual-gate-b true \
    --output "$TMPROOT/all-flags-true.json" >/dev/null
jq -e '.partition_requested == true and .brainstorm_requested == true and .manual_gate_b == true' "$TMPROOT/all-flags-true.json" >/dev/null \
    || fail "partition + brainstorm + manual Gate B all true was not persisted"

# FINDING_8: Step 0b manual-only recovery must preserve manual_gate_b=true
# even when the initial write-run-params attempt failed and the recovery path
# recreates or merges the file later.
partition_requested=false
brainstorm_requested=false
manual_requested=true
design_classification=HARD
design_classification_reason='run-params write failed; router-flag recovery'
sketch_budget=4
review_budget=full
workflow_path=HARD

recovery_missing="$TMPROOT/recovery-missing.json"
if [[ "$partition_requested" == true || "$brainstorm_requested" == true || "$manual_requested" == true ]] && command -v jq >/dev/null 2>&1; then
    if [[ -f "$recovery_missing" ]]; then
        fail "recovery-missing fixture unexpectedly existed before fallback path"
    else
        "$WRITER" \
            --classification "${design_classification:-HARD}" \
            --reason "${design_classification_reason:-run-params write failed; router-flag recovery}" \
            --source caller-forwarded \
            --sketch-budget "${sketch_budget:-4}" \
            --review-budget "${review_budget:-full}" \
            --workflow-path "${workflow_path:-HARD}" \
            --partition-requested "${partition_requested:-false}" \
            --brainstorm-requested "${brainstorm_requested:-false}" \
            --manual-gate-b "${manual_requested:-false}" \
            --output "$recovery_missing" >/dev/null
    fi
fi
jq -e '.manual_gate_b == true' "$recovery_missing" >/dev/null \
    || fail "manual-only recovery fallback did not preserve manual_gate_b=true"

recovery_merge="$TMPROOT/recovery-merge.json"
"$WRITER" \
    --classification SIMPLE \
    --reason "seed file before merge recovery" \
    --source caller-forwarded \
    --sketch-budget 2 \
    --review-budget quick \
    --workflow-path SIMPLE \
    --manual-gate-b false \
    --output "$recovery_merge" >/dev/null

_rp_merge="$TMPROOT/recovery-merge.tmp.json"
if jq -c \
    --argjson merge_p false \
    --argjson merge_b false \
    --argjson merge_m true \
    '.partition_requested = (.partition_requested == true or $merge_p) | .brainstorm_requested = (.brainstorm_requested == true or $merge_b) | .manual_gate_b = $merge_m' \
    "$recovery_merge" >"$_rp_merge"; then
    mv -f "$_rp_merge" "$recovery_merge"
else
    fail "manual-only recovery merge jq path failed"
fi
jq -e '.manual_gate_b == true' "$recovery_merge" >/dev/null \
    || fail "manual-only recovery merge did not preserve manual_gate_b=true"

echo "PASS: test-write-run-params.sh"
