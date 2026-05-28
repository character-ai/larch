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

assert_rejected_with() {
    local label="$1"
    local expected="$2"
    shift 2
    local err="$TMPROOT/${label}.err"
    local rc

    set +e
    "$WRITER" "$@" >/dev/null 2>"$err"
    rc=$?
    set -e

    [[ "$rc" == 2 ]] || fail "$label should exit 2, got $rc"
    grep -Fq "$expected" "$err" || fail "$label stderr missing '$expected': $(cat "$err")"
}

"$WRITER" \
    --classification SIMPLE \
    --output "$OUT" >/dev/null

[[ -s "$OUT" ]] || fail "writer did not create run-params.json"
jq -e '
  .schema_version == 3 and
  .design_classification == "SIMPLE" and
  has("design_classification_reason") and
  has("design_classification_source") and
  has("sketch_budget") and
  has("review_budget") and
  has("workflow_path") and
  .design_classification_reason == null and
  .design_classification_source == null and
  .sketch_budget == null and
  .review_budget == null and
  .workflow_path == null and
  .partition_requested == false and
  .brainstorm_requested == false and
  .manual_gate_b == false
' "$OUT" >/dev/null || fail "valid JSON did not match expected schema"

if "$WRITER" \
    --classification MEDIUM \
    --output "$TMPROOT/invalid-classification.json" >/dev/null 2>&1; then
    fail "invalid classification was accepted"
fi

set +e
"$WRITER" \
    --classification TRIVIAL_DOC_ONLY \
    --output "$TMPROOT/trivial.json" >/dev/null 2>"$TMPROOT/trivial.err"
trivial_rc=$?
set -e
if [[ "$trivial_rc" == 0 ]]; then
    fail "TRIVIAL_DOC_ONLY classification was accepted"
fi
[[ "$trivial_rc" == 2 ]] || fail "TRIVIAL_DOC_ONLY classification should exit 2, got $trivial_rc"
grep -Fq 'invalid --classification: TRIVIAL_DOC_ONLY' "$TMPROOT/trivial.err" \
    || fail "TRIVIAL_DOC_ONLY rejection did not report enum violation"

if ( cd "$TMPROOT" && "$WRITER" \
    --classification HARD \
    --output relative.json >/dev/null 2>&1 ); then
    fail "relative output path was accepted"
fi

if "$WRITER" \
    --classification SIMPLE \
    --partition-requested maybe \
    --output "$TMPROOT/bad-partition.json" >/dev/null 2>&1; then
    fail "invalid partition-requested was accepted"
fi

if "$WRITER" \
    --classification SIMPLE \
    --brainstorm-requested maybe \
    --output "$TMPROOT/bad-brainstorm.json" >/dev/null 2>&1; then
    fail "invalid brainstorm-requested was accepted"
fi

if "$WRITER" \
    --classification SIMPLE \
    --manual-gate-b maybe \
    --output "$TMPROOT/bad-manual-gate-b.json" >/dev/null 2>&1; then
    fail "invalid manual-gate-b was accepted"
fi

assert_rejected_with manual-gate-b-empty 'write-run-params.sh: --manual-gate-b requires a value' \
    --classification SIMPLE \
    --manual-gate-b "" \
    --output "$TMPROOT/manual-gate-b-empty.json"

assert_rejected_with manual-gate-b-missing 'write-run-params.sh: --manual-gate-b requires a value' \
    --classification SIMPLE \
    --output "$TMPROOT/manual-gate-b-missing.json" \
    --manual-gate-b

assert_rejected_with bad-sketch-budget 'invalid --sketch-budget: 5' \
    --classification SIMPLE \
    --sketch-budget 5 \
    --output "$TMPROOT/bad-sketch-budget.json"

assert_rejected_with bad-review-budget 'invalid --review-budget: medium' \
    --classification SIMPLE \
    --review-budget medium \
    --output "$TMPROOT/bad-review-budget.json"

assert_rejected_with bad-workflow-path 'invalid --workflow-path: MEDIUM' \
    --classification SIMPLE \
    --workflow-path MEDIUM \
    --output "$TMPROOT/bad-workflow-path.json"

"$WRITER" \
    --classification SIMPLE \
    --partition-requested true \
    --output "$TMPROOT/partition-true.json" >/dev/null
jq -e '.partition_requested == true' "$TMPROOT/partition-true.json" >/dev/null \
    || fail "--partition-requested true did not set JSON true"

"$WRITER" \
    --classification SIMPLE \
    --brainstorm-requested true \
    --output "$TMPROOT/brainstorm-true.json" >/dev/null
jq -e '.brainstorm_requested == true' "$TMPROOT/brainstorm-true.json" >/dev/null \
    || fail "--brainstorm-requested true did not set JSON true"

"$WRITER" \
    --classification SIMPLE \
    --manual-gate-b true \
    --output "$TMPROOT/manual-gate-b-true.json" >/dev/null
jq -e '.manual_gate_b == true' "$TMPROOT/manual-gate-b-true.json" >/dev/null \
    || fail "--manual-gate-b true did not set JSON true"

"$WRITER" \
    --classification SIMPLE \
    --manual-gate-b false \
    --output "$TMPROOT/manual-gate-b-false.json" >/dev/null
jq -e '.manual_gate_b == false' "$TMPROOT/manual-gate-b-false.json" >/dev/null \
    || fail "--manual-gate-b false did not set JSON false"

"$WRITER" \
    --classification SIMPLE \
    --partition-requested true \
    --brainstorm-requested true \
    --manual-gate-b true \
    --output "$TMPROOT/all-flags-true.json" >/dev/null
jq -e '.partition_requested == true and .brainstorm_requested == true and .manual_gate_b == true' "$TMPROOT/all-flags-true.json" >/dev/null \
    || fail "partition + brainstorm + manual Gate B all true was not persisted"

"$WRITER" \
    --classification HARD \
    --reason "argv tier: --hard" \
    --source caller-forwarded \
    --sketch-budget 4 \
    --review-budget full \
    --workflow-path HARD \
    --partition-requested true \
    --brainstorm-requested true \
    --manual-gate-b true \
    --output "$TMPROOT/all-v3-flags.json" >/dev/null
jq -e '
  .schema_version == 3 and
  .design_classification == "HARD" and
  .design_classification_reason == "argv tier: --hard" and
  .design_classification_source == "caller-forwarded" and
  .sketch_budget == 4 and
  .review_budget == "full" and
  .workflow_path == "HARD" and
  .partition_requested == true and
  .brainstorm_requested == true and
  .manual_gate_b == true
' "$TMPROOT/all-v3-flags.json" >/dev/null || fail "full v3 flag set was not persisted"

"$WRITER" \
    --classification SIMPLE \
    --reason "" \
    --source "" \
    --sketch-budget "" \
    --review-budget "" \
    --workflow-path "" \
    --output "$TMPROOT/empty-v3-fields.json" >/dev/null
jq -e '
  .design_classification_reason == null and
  .design_classification_source == null and
  .sketch_budget == null and
  .review_budget == null and
  .workflow_path == null
' "$TMPROOT/empty-v3-fields.json" >/dev/null || fail "empty optional v3 fields did not emit JSON null"

"$WRITER" \
    --classification SIMPLE \
    --reason "free form" \
    --source caller-forwarded \
    --sketch-budget 0 \
    --review-budget full \
    --workflow-path SIMPLE \
    --output "$TMPROOT/simple-v3-fields.json" >/dev/null
jq -e '
  .design_classification_reason == "free form" and
  .design_classification_source == "caller-forwarded" and
  .sketch_budget == 0 and
  .review_budget == "full" and
  .workflow_path == "SIMPLE"
' "$TMPROOT/simple-v3-fields.json" >/dev/null || fail "v3 fields did not round-trip by exact name"

echo "PASS: test-write-run-params.sh"
