#!/usr/bin/env bash
# test-token-report-summary-format.sh — bug-4: dollar-primary --summary line (DE-2622).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO/scripts/token-report.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

ROOT="${TMPDIR:-/tmp}"
TMP=$(mktemp -d "$ROOT/test-tr-sumfmt.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

LEDGER="$TMP/ledger.jsonl"
TRANSCRIPT="$TMP/transcript.jsonl"
cat > "$LEDGER" <<'JSONL'
{"type":"mark","step":"Step 1","ts":"2026-05-22T00:00:00Z"}
JSONL
cat > "$TRANSCRIPT" <<'JSONL'
{"type":"assistant","timestamp":"2026-05-22T00:00:01.000Z","requestId":"a","message":{"id":"m1","usage":{"input_tokens":1000000,"cache_read_input_tokens":0,"cache_creation_input_tokens":0,"output_tokens":0}}}
JSONL

line=$("$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --summary)
case "$line" in
    *'Cost: TOTAL'*) ;;
    *) fail "summary missing Cost: TOTAL: $line" ;;
esac
case "$line" in
    *'Claude $'*) ;;
    *) fail "summary missing Claude dollars: $line" ;;
esac
case "$line" in
    *'Codex $'*) ;;
    *) fail "summary missing Codex dollars: $line" ;;
esac
case "$line" in
    *'Cursor $'*) ;;
    *) fail "summary missing Cursor dollars: $line" ;;
esac
case "$line" in
    *'Tokens:'*) ;;
    *) fail "summary missing Tokens: $line" ;;
esac
pass 'token-report --summary dollar-primary shape'

printf 'PASS: test-token-report-summary-format.sh\n'
