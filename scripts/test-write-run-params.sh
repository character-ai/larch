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
  .workflow_path == "SIMPLE"
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
  .sketch_budget == 0
' "$TMPROOT/trivial.json" >/dev/null \
    || fail "trivial preset JSON did not match expected classification fields"

if "$WRITER" \
    --classification SIMPLE \
    --reason bad \
    --source router-pre-design \
    --sketch-budget 2 \
    --review-budget quick \
    --workflow-path SIMPLE \
    --output "$TMPROOT/rejected-source.json" >/dev/null 2>&1; then
    fail "obsolete router-pre-design source was accepted"
fi

echo "PASS: test-write-run-params.sh"
