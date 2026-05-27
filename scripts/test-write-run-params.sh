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

"$WRITER" \
    --classification SIMPLE \
    --output "$OUT" >/dev/null

[[ -s "$OUT" ]] || fail "writer did not create run-params.json"
jq -e '
  .schema_version == 2 and
  .design_classification == "SIMPLE" and
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

echo "PASS: test-write-run-params.sh"
