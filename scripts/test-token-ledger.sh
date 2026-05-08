#!/usr/bin/env bash
# test-token-ledger.sh — offline regression harness for token-ledger.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/token-ledger.sh"
READ_SESSION_ENV_KEY="$REPO_ROOT/scripts/read-session-env-key.sh"
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

SESSION_ENV_A="$TMP/session-env-A.sh"
SESSION_ENV_B="$TMP/session-env-B.sh"
printf 'LARCH_TOKEN_SESSION_ID=fresh-id-A\n' > "$SESSION_ENV_A"
printf 'LARCH_TOKEN_SESSION_ID=fresh-id-B\n' > "$SESSION_ENV_B"
rehydrated_a=$("$READ_SESSION_ENV_KEY" --file "$SESSION_ENV_A" --key LARCH_TOKEN_SESSION_ID --default "")
rehydrated_b=$("$READ_SESSION_ENV_KEY" --file "$SESSION_ENV_B" --key LARCH_TOKEN_SESSION_ID --default "")
rehydrated_path_a=$(env -u IMPLEMENT_TMPDIR LARCH_TOKEN_SESSION_ID="$rehydrated_a" "$SCRIPT" dump | sed -n '1p')
rehydrated_path_b=$(env -u IMPLEMENT_TMPDIR LARCH_TOKEN_SESSION_ID="$rehydrated_b" "$SCRIPT" dump | sed -n '1p')
assert_contains "rehydrated fixture A" "$(sha256 "fresh-id-A")" "$rehydrated_path_a"
assert_contains "rehydrated fixture B" "$(sha256 "fresh-id-B")" "$rehydrated_path_b"
if [[ "$rehydrated_path_a" != "$rehydrated_path_b" ]]; then pass; else fail "rehydrated fixtures should resolve distinct ledger paths"; fi

OVERWRITE_TMP="$TMP/overwrite"
mkdir -p "$OVERWRITE_TMP"
printf 'fresh-overwrite\n' > "$OVERWRITE_TMP/session-id"
overwrite_file_id=$(LARCH_TOKEN_SESSION_ID=stale IMPLEMENT_TMPDIR="$OVERWRITE_TMP" bash -c '
    if [[ -n "${IMPLEMENT_TMPDIR:-}" && -s "${IMPLEMENT_TMPDIR}/session-id" ]]; then
        file_id=$(tr -d "\r\n" < "${IMPLEMENT_TMPDIR}/session-id" 2>/dev/null || true)
        if [[ -n "$file_id" ]]; then export LARCH_TOKEN_SESSION_ID="$file_id"; fi
    fi
    printf "%s\n" "$LARCH_TOKEN_SESSION_ID"
')
assert_eq "canonical tmpdir overwrite" "fresh-overwrite" "$overwrite_file_id"

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

# `--ledger PATH` "anywhere in argv" pre-pass (issue #1351 Gap 2). Pre-pass
# strips every `--ledger PATH` pair from anywhere in argv, last-wins. The
# subcommand position is irrelevant.

# Subcommand-then-flag form (mark): pre-pass before /bump-version replaced the
# "unknown record-vendor key: --ledger" warnings on this exact shape.
LEDGER_AFTER="$TMP/after.jsonl"
"$SCRIPT" mark "Step after-subcmd" --ledger "$LEDGER_AFTER"
if [[ -f "$LEDGER_AFTER" ]] && jq -e 'select(.type=="mark" and .step=="Step after-subcmd")' "$LEDGER_AFTER" >/dev/null; then pass; else fail "--ledger after subcommand should record the mark: $(cat "$LEDGER_AFTER" 2>/dev/null)"; fi

# Tail position (record-vendor with --ledger as the trailing pair).
LEDGER_TAIL="$TMP/tail.jsonl"
"$SCRIPT" record-vendor codex total=99 raw=codex_implement --ledger "$LEDGER_TAIL"
if [[ -f "$LEDGER_TAIL" ]] && jq -e 'select(.type=="vendor" and .vendor=="codex" and .total==99)' "$LEDGER_TAIL" >/dev/null; then pass; else fail "--ledger at tail should record the vendor row: $(cat "$LEDGER_TAIL" 2>/dev/null)"; fi

# Last-wins precedence when --ledger appears multiple times. The first ledger
# is never created (validate_under_tmp only mkdir's the parent); the last
# ledger is the only one written to.
LEDGER_FIRST="$TMP/first.jsonl"
LEDGER_LAST="$TMP/last.jsonl"
"$SCRIPT" --ledger "$LEDGER_FIRST" mark "Step last-wins" --ledger "$LEDGER_LAST"
if [[ -f "$LEDGER_LAST" ]] && jq -e 'select(.type=="mark" and .step=="Step last-wins")' "$LEDGER_LAST" >/dev/null; then pass; else fail "last --ledger should be the one written to: last=$(cat "$LEDGER_LAST" 2>/dev/null)"; fi
if [[ ! -e "$LEDGER_FIRST" ]] || [[ ! -s "$LEDGER_FIRST" ]]; then pass; else fail "first --ledger should not have been written to: $(cat "$LEDGER_FIRST" 2>/dev/null)"; fi

total=$((PASS + FAIL))
if (( FAIL == 0 )); then
    echo "PASS: test-token-ledger.sh — $PASS/$total assertions"
else
    echo "FAIL: test-token-ledger.sh — $FAIL/$total assertions failed" >&2
    exit 1
fi
