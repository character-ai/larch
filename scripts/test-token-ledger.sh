#!/usr/bin/env bash
# test-token-ledger.sh — offline regression harness for token-ledger.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/token-ledger.sh"
PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1" >&2; FAIL=$((FAIL + 1)); }

assert_contains() {
    case "$3" in
        *"$2"*) pass ;;
        *) fail "$1 missing '$2': $3" ;;
    esac
}

assert_eq() {
    if [[ "$2" == "$3" ]]; then pass; else fail "$1 expected '$2' got '$3'"; fi
}

sha256() {
    if command -v shasum >/dev/null 2>&1; then
        printf '%s' "$1" | LC_ALL=C shasum -a 256 | awk '{print $1}'
    else
        printf '%s' "$1" | sha256sum | awk '{print $1}'
    fi
}

ROOT="${TMPDIR:-/tmp}"
TMP=$(mktemp -d "$ROOT/test-token-ledger.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

LEDGER="$TMP/ledger.jsonl"
"$SCRIPT" --ledger "$LEDGER" mark "Step 1 - fixture"
"$SCRIPT" --ledger "$LEDGER" record-vendor codex total=123 raw=codex_implement

if jq -e 'select(.type=="mark" and .step=="Step 1 - fixture")' "$LEDGER" >/dev/null; then pass; else fail "mark JSON missing"; fi
if jq -e 'select(.type=="vendor" and .vendor=="codex" and .total==123 and .raw=="codex_implement")' "$LEDGER" >/dev/null; then pass; else fail "vendor JSON missing"; fi

# GNU stat (-c) probed first because BSD stat's `-f` flag means "filesystem"
# rather than "format" on Linux, where it succeeds with completely different
# output (a multi-line filesystem report) instead of failing — that breaks
# the `|| fallback` pattern when the BSD flag is tried first on Linux.
# Linux GNU stat: `-c %a` returns the octal mode bits and exits 0.
# macOS BSD stat: `-c` is unrecognized → fails → fallback to `-f %Lp`.
mode=$(stat -c %a "$LEDGER" 2>/dev/null || stat -f %Lp "$LEDGER" 2>/dev/null)
assert_eq "ledger mode" "600" "$mode"

dump=$("$SCRIPT" --ledger "$LEDGER" dump)
dump_path=$(printf '%s\n' "$dump" | sed -n '1p')
if [[ -f "$dump_path" ]]; then pass; else fail "dump path should point to ledger file: $dump_path"; fi
assert_contains "dump json" '"type":"mark"' "$dump"

SESSION_TMP="$TMP/session"
mkdir -p "$SESSION_TMP"
printf 'session-file-id\n' > "$SESSION_TMP/session-id"
env_path=$(LARCH_TOKEN_SESSION_ID=env-id IMPLEMENT_TMPDIR="$SESSION_TMP" "$SCRIPT" dump | sed -n '1p')
file_path=$(IMPLEMENT_TMPDIR="$SESSION_TMP" "$SCRIPT" dump | sed -n '1p')
env_slug=$(sha256 "env-id")
file_slug=$(sha256 "session-file-id")
assert_contains "env precedence" "$env_slug" "$env_path"
assert_contains "session-file fallback" "$file_slug" "$file_path"

unsafe_path=$(LARCH_TOKEN_SESSION_ID=$'../bad/id\nx' "$SCRIPT" dump | sed -n '1p')
case "$unsafe_path" in
    *".."*|*"/bad/"*) fail "unsafe raw id leaked into path: $unsafe_path" ;;
    *) pass ;;
esac

BAD="$TMP/../escape.jsonl"
"$SCRIPT" --ledger "$BAD" mark "bad" 2>"$TMP/bad.err" || true
if [[ ! -e "$BAD" ]] && grep -Fq "WARNING" "$TMP/bad.err"; then pass; else fail "--ledger escape should warn and not write"; fi

RAW=$'cursor_"quoted"\nreview'
"$SCRIPT" --ledger "$LEDGER" record-vendor cursor total=7 raw="$RAW"
if jq -e --arg raw "$RAW" 'select(.type=="vendor" and .vendor=="cursor" and .raw==$raw)' "$LEDGER" >/dev/null; then pass; else fail "raw field was not JSON-safe"; fi

total=$((PASS + FAIL))
if (( FAIL == 0 )); then
    echo "PASS: test-token-ledger.sh — $PASS/$total assertions"
else
    echo "FAIL: test-token-ledger.sh — $FAIL/$total assertions failed" >&2
    exit 1
fi
