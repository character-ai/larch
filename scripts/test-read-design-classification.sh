#!/usr/bin/env bash
# Regression harness for scripts/read-design-classification.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SUBJECT="$REPO_ROOT/scripts/read-design-classification.sh"

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-read-design-classification.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

SIMPLE_JSON="$TMPROOT/simple.json"
cat >"$SIMPLE_JSON" <<'JSON'
{"schema_version":2,"design_classification":"SIMPLE","partition_requested":false,"brainstorm_requested":false}
JSON
[[ "$("$SUBJECT" "$SIMPLE_JSON" 2>"$TMPROOT/simple.err")" == "SIMPLE" ]] || fail "SIMPLE classification did not round-trip"
[[ ! -s "$TMPROOT/simple.err" ]] || fail "valid SIMPLE classification should not warn"

HARD_DIR="$TMPROOT/hard-dir"
mkdir -p "$HARD_DIR"
cat >"$HARD_DIR/run-params.json" <<'JSON'
{"schema_version":2,"design_classification":"HARD","partition_requested":false,"brainstorm_requested":false}
JSON
out_hard="$(DESIGN_TMPDIR="$HARD_DIR" "$SUBJECT" 2>"$TMPROOT/hard.err")"
[[ "$out_hard" == "HARD" ]] || fail "DESIGN_TMPDIR fallback did not resolve HARD"
[[ ! -s "$TMPROOT/hard.err" ]] || fail "valid HARD classification should not warn"

INVALID_JSON="$TMPROOT/invalid.json"
cat >"$INVALID_JSON" <<'JSON'
{"schema_version":2,"design_classification":"BOGUS","partition_requested":false,"brainstorm_requested":false}
JSON
out_invalid="$("$SUBJECT" "$INVALID_JSON" 2>"$TMPROOT/invalid.err")"
[[ "$out_invalid" == "HARD" ]] || fail "invalid classification must default to HARD"
grep -Fq '**⚠ read-design-classification: design_classification missing or invalid; defaulting to HARD**' "$TMPROOT/invalid.err" \
    || fail "invalid classification warning missing"

out_missing="$("$SUBJECT" "$TMPROOT/missing.json" 2>"$TMPROOT/missing.err")"
[[ "$out_missing" == "HARD" ]] || fail "missing file must default to HARD"
grep -Fq '**⚠ read-design-classification: run-params not readable:' "$TMPROOT/missing.err" \
    || fail "missing file warning missing"

printf 'PASS: test-read-design-classification.sh\n'
