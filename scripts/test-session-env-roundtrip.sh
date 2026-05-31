#!/usr/bin/env bash
# test-session-env-roundtrip.sh — regression harness for issue #1513.
#
# Covers:
#   A. read-session-env-key.sh extracts values containing '=' without
#      truncation (was: awk -F= '{print $2}' truncated at first '=').
#   B. write-session-env.sh validates --timing-ledger paths via the
#      regex/length guard ^[A-Za-z0-9_./~+-]{1,512}$ shared with
#      --claude-source-file.
#   C. write-session-env.sh validates and persists PREV_IMPLEMENT_TMPDIR.
#   D. write-session-env.sh validates and persists CLAUDE_PLUGIN_ROOT.
#   E. write-session-env.sh validates and persists LARCH_DYNAMIC_ARCHETYPES_MAX.
#   F. write-design-current-env.sh rejects invalid CLAUDE_PLUGIN_ROOT values.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
READ_SCRIPT="$REPO_ROOT/scripts/read-session-env-key.sh"
WRITE_SCRIPT="$REPO_ROOT/scripts/write-session-env.sh"
WRITE_DESIGN_CURRENT_ENV_SCRIPT="$REPO_ROOT/scripts/write-design-current-env.sh"
PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1" >&2; FAIL=$((FAIL + 1)); }

assert_eq() {
    if [[ "$2" == "$3" ]]; then pass; else fail "$1: expected '$2' got '$3'"; fi
}

assert_contains() {
    case "$3" in
        *"$2"*) pass ;;
        *) fail "$1: missing '$2' in: $3" ;;
    esac
}

TMPDIR_TEST="$(mktemp -d "${TMPDIR:-/tmp}/test-session-env-roundtrip.XXXXXX")"
trap 'rm -rf "$TMPDIR_TEST"' EXIT

# ------------------------------------------------------------
# A. read-session-env-key.sh — value containing '='
# ------------------------------------------------------------

ENV_FILE="$TMPDIR_TEST/session-env.sh"
cat > "$ENV_FILE" <<'EOF'
COMPLEX=a=b=c
EMPTY=
ENDS_EQ=foo=
TRAILING_LIST=k1=v1,k2=v2
PLAIN=hello
EOF

# A.1 — value with multiple '=' must not truncate at first separator.
got=$("$READ_SCRIPT" --file "$ENV_FILE" --key COMPLEX)
assert_eq "A.1 multi-eq value" "a=b=c" "$got"

# A.2 — empty value reads as empty.
got=$("$READ_SCRIPT" --file "$ENV_FILE" --key EMPTY)
assert_eq "A.2 empty value" "" "$got"

# A.3 — trailing '=' preserved.
got=$("$READ_SCRIPT" --file "$ENV_FILE" --key ENDS_EQ)
assert_eq "A.3 trailing eq" "foo=" "$got"

# A.4 — comma-separated kv-list value (typical CSV-of-KVs case).
got=$("$READ_SCRIPT" --file "$ENV_FILE" --key TRAILING_LIST)
assert_eq "A.4 csv-kv list" "k1=v1,k2=v2" "$got"

# A.5 — plain value still works.
got=$("$READ_SCRIPT" --file "$ENV_FILE" --key PLAIN)
assert_eq "A.5 plain value" "hello" "$got"

# A.6 — missing key with --default returns the default.
got=$("$READ_SCRIPT" --file "$ENV_FILE" --key NOPE --default fallback)
assert_eq "A.6 missing with default" "fallback" "$got"

# A.6b — present-but-empty value with --default returns the default
# (matches the contract documented in scripts/read-session-env-key.md).
got=$("$READ_SCRIPT" --file "$ENV_FILE" --key EMPTY --default fallback)
assert_eq "A.6b present-empty with default" "fallback" "$got"

# A.6c — empty --file with --default returns the default (closes #1563
# round-2 review: standalone /design and /review pass an empty
# SESSION_ENV_PATH and would otherwise emit "--file is required" stderr
# noise, also tripping `set -e` in callers).
got=$("$READ_SCRIPT" --file "" --key WHATEVER --default fallback)
assert_eq "A.6c empty file with default" "fallback" "$got"

# A.6d — empty --file without --default keeps the usage error (exit 1).
if "$READ_SCRIPT" --file "" --key WHATEVER >/dev/null 2>&1; then
    fail "A.6d: empty --file without --default should exit 1"
else
    pass
fi

# A.6e — empty --file with --default but missing --key still errors with
# "--key is required" (closes #1563 round-3 review: --key validation
# must run before the empty-file/default branch so an invocation that
# forgets --key cannot silently print the default).
if "$READ_SCRIPT" --file "" --default fallback >/dev/null 2>&1; then
    fail "A.6e: empty --file + --default without --key should exit 1"
else
    pass
fi

# A.6f — OMITTED --file (not just explicitly empty) with --default still
# errors with "--file is required" (closes #1563 round-4 review: the
# default-on-empty-file tolerance is gated on --file being explicitly
# present so a caller who simply forgot to pass --file does NOT silently
# get the default and mask caller bugs).
if "$READ_SCRIPT" --key X --default fallback >/dev/null 2>&1; then
    fail "A.6f: omitted --file + --default + --key should exit 1"
else
    pass
fi

# A.7 — KEY prefix collision: a key whose name is a prefix of another must
# match exactly (not match the longer-named key's line). Locks the
# whole-key-plus-equals match in the corrected awk.
cat > "$ENV_FILE" <<'EOF'
FOO=short
FOOBAR=long
EOF
got=$("$READ_SCRIPT" --file "$ENV_FILE" --key FOO)
assert_eq "A.7 prefix collision" "short" "$got"
got=$("$READ_SCRIPT" --file "$ENV_FILE" --key FOOBAR)
assert_eq "A.7 longer key" "long" "$got"

# ------------------------------------------------------------
# B. write-session-env.sh — --timing-ledger path validation
# ------------------------------------------------------------

OUT="$TMPDIR_TEST/out.sh"

# B.1 — valid path is accepted.
if "$WRITE_SCRIPT" \
    --output "$OUT" --repo a/b --repo-unavailable false \
    --timing-ledger "$TMPDIR_TEST/timing-ledger.tsv" 2>/dev/null; then
    pass
else
    fail "B.1 valid timing-ledger rejected"
fi
# Verify the value round-trips through the writer.
got=$("$READ_SCRIPT" --file "$OUT" --key LARCH_TIMING_LEDGER)
assert_eq "B.1 value persisted" "$TMPDIR_TEST/timing-ledger.tsv" "$got"

# B.2 — path with disallowed characters is rejected with the expected error.
if err=$("$WRITE_SCRIPT" \
    --output "$OUT" --repo a/b --repo-unavailable false \
    --timing-ledger "/tmp/bad ledger.tsv" 2>&1); then
    fail "B.2 path with space accepted: $err"
else
    assert_contains "B.2 error message" "Invalid --timing-ledger" "$err"
fi

# B.3 — overlong path (> 512 chars) is rejected.
LONG="$(printf '/tmp/%.0s' {1..200})ledger.tsv"  # ~ 800 chars
if err=$("$WRITE_SCRIPT" \
    --output "$OUT" --repo a/b --repo-unavailable false \
    --timing-ledger "$LONG" 2>&1); then
    fail "B.3 overlong path accepted"
else
    assert_contains "B.3 error message" "Invalid --timing-ledger" "$err"
fi

# B.4 — empty / absent --timing-ledger continues to be accepted.
if "$WRITE_SCRIPT" \
    --output "$OUT" --repo a/b --repo-unavailable false 2>/dev/null; then
    pass
else
    fail "B.4 absent timing-ledger rejected"
fi

# ------------------------------------------------------------
# C. write-session-env.sh — --prev-implement-tmpdir validation
# ------------------------------------------------------------

if "$WRITE_SCRIPT" \
    --output "$OUT" --repo a/b --repo-unavailable false \
    --prev-implement-tmpdir "$TMPDIR_TEST/prev-implement" 2>/dev/null; then
    pass
else
    fail "C.1 valid prev-implement-tmpdir rejected"
fi
got=$("$READ_SCRIPT" --file "$OUT" --key PREV_IMPLEMENT_TMPDIR)
assert_eq "C.1 value persisted" "$TMPDIR_TEST/prev-implement" "$got"

if err=$("$WRITE_SCRIPT" \
    --output "$OUT" --repo a/b --repo-unavailable false \
    --prev-implement-tmpdir "relative/path" 2>&1); then
    fail "C.2 relative prev-implement-tmpdir accepted"
else
    assert_contains "C.2 error message" "Invalid --prev-implement-tmpdir" "$err"
fi

# ------------------------------------------------------------
# D. write-session-env.sh — CLAUDE_PLUGIN_ROOT validation
# ------------------------------------------------------------

if CLAUDE_PLUGIN_ROOT="$TMPDIR_TEST/plugin-root" "$WRITE_SCRIPT" \
    --output "$OUT" --repo a/b --repo-unavailable false 2>/dev/null; then
    pass
else
    fail "D.1 valid CLAUDE_PLUGIN_ROOT rejected"
fi
got=$("$READ_SCRIPT" --file "$OUT" --key LARCH_CLAUDE_PLUGIN_ROOT)
assert_eq "D.1 value persisted" "$TMPDIR_TEST/plugin-root" "$got"

if err=$(CLAUDE_PLUGIN_ROOT="/tmp/bad plugin-root" "$WRITE_SCRIPT" \
    --output "$OUT" --repo a/b --repo-unavailable false 2>&1); then
    fail "D.2 CLAUDE_PLUGIN_ROOT with space accepted"
else
    assert_contains "D.2 error message" "Invalid CLAUDE_PLUGIN_ROOT" "$err"
fi

if err=$(CLAUDE_PLUGIN_ROOT="relative/plugin-root" "$WRITE_SCRIPT" \
    --output "$OUT" --repo a/b --repo-unavailable false 2>&1); then
    fail "D.3 relative CLAUDE_PLUGIN_ROOT accepted"
else
    assert_contains "D.3 error message" "Invalid CLAUDE_PLUGIN_ROOT" "$err"
fi

# ------------------------------------------------------------
# E. write-session-env.sh — --dynamic-archetypes validation
# ------------------------------------------------------------

if "$WRITE_SCRIPT" \
    --output "$OUT" --repo a/b --repo-unavailable false \
    --dynamic-archetypes 4 2>/dev/null; then
    pass
else
    fail "E.1 valid dynamic-archetypes rejected"
fi
got=$("$READ_SCRIPT" --file "$OUT" --key LARCH_DYNAMIC_ARCHETYPES_MAX)
assert_eq "E.1 value persisted" "4" "$got"

if err=$("$WRITE_SCRIPT" \
    --output "$OUT" --repo a/b --repo-unavailable false \
    --dynamic-archetypes 9 2>&1); then
    fail "E.2 invalid dynamic-archetypes accepted"
else
    assert_contains "E.2 error message" "Invalid --dynamic-archetypes" "$err"
fi

# ------------------------------------------------------------
# F. write-design-current-env.sh — CLAUDE_PLUGIN_ROOT validation
# ------------------------------------------------------------

design_out="$TMPDIR_TEST/design-source-env.sh"
design_tmpdir="$TMPDIR_TEST/design-tmpdir"
design_home="$TMPDIR_TEST/design-home"
mkdir -p "$design_tmpdir"
mkdir -p "$design_home"

if err=$(HOME="$design_home" CLAUDE_PLUGIN_ROOT="/tmp/bad plugin-root" "$WRITE_DESIGN_CURRENT_ENV_SCRIPT" \
    --output "$design_out" \
    --design-tmpdir "$design_tmpdir" \
    --session-id test-design-roundtrip \
    --claude-pid 7654321 2>&1); then
    fail "F.1 CLAUDE_PLUGIN_ROOT with space accepted by write-design-current-env"
else
    assert_contains "F.1 error message" "Invalid CLAUDE_PLUGIN_ROOT" "$err"
fi

if err=$(HOME="$design_home" CLAUDE_PLUGIN_ROOT="relative/plugin-root" "$WRITE_DESIGN_CURRENT_ENV_SCRIPT" \
    --output "$design_out" \
    --design-tmpdir "$design_tmpdir" \
    --session-id test-design-roundtrip \
    --claude-pid 7654321 2>&1); then
    fail "F.2 relative CLAUDE_PLUGIN_ROOT accepted by write-design-current-env"
else
    assert_contains "F.2 error message" "Invalid CLAUDE_PLUGIN_ROOT" "$err"
fi

# ------------------------------------------------------------
# G. write-session-env.sh — plugin-root.env sibling
# ------------------------------------------------------------

plugin_root_value="$TMPDIR_TEST/plugin-root"
plugin_out="$TMPDIR_TEST/plugin-root-session-env.sh"
plugin_root_env="$TMPDIR_TEST/plugin-root.env"

if CLAUDE_PLUGIN_ROOT="$plugin_root_value" "$WRITE_SCRIPT" \
    --output "$plugin_out" --repo a/b --repo-unavailable false 2>/dev/null; then
    pass
else
    fail "G.1 plugin-root.env emit rejected"
fi

if [[ ! -f "$plugin_root_env" ]]; then
    fail "G.1 plugin-root.env missing"
else
    pass
fi

if ! grep -Fxq "CLAUDE_PLUGIN_ROOT=$plugin_root_value" "$plugin_root_env"; then
    fail "G.1 plugin-root.env missing CLAUDE_PLUGIN_ROOT line"
else
    pass
fi

if ! grep -Fxq 'export CLAUDE_PLUGIN_ROOT' "$plugin_root_env"; then
    fail "G.1 plugin-root.env missing export line"
else
    pass
fi

if ! ( unset CLAUDE_PLUGIN_ROOT
       # shellcheck disable=SC1090
       . "$plugin_root_env"
       [[ "$CLAUDE_PLUGIN_ROOT" == "$plugin_root_value" ]] ); then
    fail "G.1 plugin-root.env does not source cleanly"
else
    pass
fi

devnull_env="$TMPDIR_TEST/devnull-plugin-root.env"
if CLAUDE_PLUGIN_ROOT="$plugin_root_value" "$WRITE_SCRIPT" \
    --output /dev/null --repo a/b --repo-unavailable false 2>/dev/null; then
    pass
else
    fail "G.2 /dev/null output rejected"
fi
if [[ -f "$devnull_env" || -f /dev/plugin-root.env ]]; then
    fail "G.2 plugin-root.env written for /dev/null output"
else
    pass
fi

unset_dir="$TMPDIR_TEST/unset-plugin-root"
mkdir -p "$unset_dir"
rm -f "$TMPDIR_TEST/plugin-root.env"
unset_out="$unset_dir/session-env.sh"
if env -u CLAUDE_PLUGIN_ROOT "$WRITE_SCRIPT" \
    --output "$unset_out" --repo a/b --repo-unavailable false 2>/dev/null; then
    pass
else
    fail "G.3 empty CLAUDE_PLUGIN_ROOT rejected"
fi
if [[ -f "$unset_dir/plugin-root.env" ]]; then
    fail "G.3 plugin-root.env written when CLAUDE_PLUGIN_ROOT unset"
else
    pass
fi

# G.4 — resume-tail sibling sync via emit_plugin_root_env (legacy tmpdir).
resume_tmp="$TMPDIR_TEST/resume-tail"
mkdir -p "$resume_tmp"
cat > "$resume_tmp/session-env.sh" <<EOF
REPO=a/b
REPO_UNAVAILABLE=false
FORKED_TARGET=false
LARCH_CLAUDE_PLUGIN_ROOT=$plugin_root_value
EOF

# shellcheck source=scripts/write-session-env.sh
. "$WRITE_SCRIPT"
emit_plugin_root_env "$resume_tmp/plugin-root.env" "$plugin_root_value"
if [[ ! -f "$resume_tmp/plugin-root.env" ]]; then
    fail "G.4 resume-tail plugin-root.env missing"
else
    pass
fi
if ! ( unset CLAUDE_PLUGIN_ROOT
       # shellcheck disable=SC1090
       . "$resume_tmp/plugin-root.env"
       [[ "$CLAUDE_PLUGIN_ROOT" == "$plugin_root_value" ]] ); then
    fail "G.4 resume-tail plugin-root.env does not source cleanly"
else
    pass
fi

# G.5 — emit_plugin_root_env returns 0 on invalid value under set -uo pipefail.
if ( set -uo pipefail
     # shellcheck source=scripts/write-session-env.sh
     . "$WRITE_SCRIPT"
     emit_plugin_root_env "$TMPDIR_TEST/invalid-plugin-root.env" '/tmp/bad plugin-root'
     [[ ! -f "$TMPDIR_TEST/invalid-plugin-root.env" ]] ); then
    pass
else
    fail "G.5 emit_plugin_root_env invalid value should return 0 without aborting parent"
fi

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

echo "test-session-env-roundtrip.sh: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
