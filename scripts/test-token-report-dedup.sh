#!/usr/bin/env bash
# test-token-report-dedup.sh — pin JSONL dedup for Claude usage rows (DE-2622).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/token-report.sh"
PASS=0
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; PASS=$((PASS + 1)); }

ROOT="${TMPDIR:-/tmp}"
TMP=$(mktemp -d "$ROOT/test-token-report-dedup.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

LEDGER="$TMP/ledger.jsonl"
TRANSCRIPT="$TMP/transcript.jsonl"
cat > "$LEDGER" <<'JSONL'
{"type":"mark","step":"Step 1","ts":"2026-05-22T00:00:00Z"}
JSONL
# Three identical (rid, mid, usage) rows → one logical response; one distinct tuple.
# One row with null ids but different usage fingerprint must not collapse with another null-id row.
cat > "$TRANSCRIPT" <<'JSONL'
{"type":"assistant","timestamp":"2026-05-22T00:00:01.000Z","requestId":"dup-a","message":{"id":"m1","usage":{"input_tokens":10,"cache_read_input_tokens":0,"cache_creation_input_tokens":0,"output_tokens":0}}}
{"type":"assistant","timestamp":"2026-05-22T00:00:01.001Z","requestId":"dup-a","message":{"id":"m1","usage":{"input_tokens":10,"cache_read_input_tokens":0,"cache_creation_input_tokens":0,"output_tokens":0}}}
{"type":"assistant","timestamp":"2026-05-22T00:00:01.002Z","requestId":"dup-a","message":{"id":"m1","usage":{"input_tokens":10,"cache_read_input_tokens":0,"cache_creation_input_tokens":0,"output_tokens":0}}}
{"type":"assistant","timestamp":"2026-05-22T00:00:02.000Z","requestId":"uniq-b","message":{"id":"m2","usage":{"input_tokens":50,"cache_read_input_tokens":0,"cache_creation_input_tokens":0,"output_tokens":0}}}
{"type":"assistant","timestamp":"2026-05-22T00:00:03.000Z","message":{"usage":{"input_tokens":1,"cache_read_input_tokens":0,"cache_creation_input_tokens":0,"output_tokens":0}}}
{"type":"assistant","timestamp":"2026-05-22T00:00:03.001Z","message":{"usage":{"input_tokens":2,"cache_read_input_tokens":0,"cache_creation_input_tokens":0,"output_tokens":0}}}
JSONL

# Expected Claude input: 10 (dup group) + 50 + 1 + 2 = 63
json_out=$("$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --full --format json)
if printf '%s' "$json_out" | jq -e '.claude.totals.input == 63' >/dev/null; then
    pass "deduped Claude input totals (rid/mid groups + null-id fingerprint)"
else
    fail "expected .claude.totals.input==63, got: $(printf '%s' "$json_out" | jq -c '.claude.totals')"
fi

printf 'PASS: test-token-report-dedup.sh — %s checks\n' "$PASS"
