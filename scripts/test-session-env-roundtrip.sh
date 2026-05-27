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
#   F. write-session-env.sh refreshes numeric cache-root mtimes and no-ops for
#      non-numeric plugin-root basenames.
#   G. session-setup.sh refreshes numeric cache-root mtimes before setup.
#   H. write-design-current-env.sh refreshes numeric cache-root mtimes and
#      no-ops for non-numeric plugin-root basenames.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
READ_SCRIPT="$REPO_ROOT/scripts/read-session-env-key.sh"
WRITE_SCRIPT="$REPO_ROOT/scripts/write-session-env.sh"
SESSION_SETUP_SCRIPT="$REPO_ROOT/scripts/session-setup.sh"
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

stat_mtime() {
    local path="$1"
    local mt
    if mt=$(stat -c '%Y' -- "$path" 2>/dev/null) && [[ "$mt" =~ ^[0-9]+$ ]]; then
        printf '%s\n' "$mt"
        return 0
    fi
    if mt=$(stat -f '%m' -- "$path" 2>/dev/null) && [[ "$mt" =~ ^[0-9]+$ ]]; then
        printf '%s\n' "$mt"
        return 0
    fi
    printf '0\n'
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
# F. write-session-env.sh — cache-root mtime touch behavior
# ------------------------------------------------------------

numeric_root="$TMPDIR_TEST/cache/42.5.36"
mkdir -p "$numeric_root"
touch -t 200001010001 -- "$numeric_root"
before=$(stat_mtime "$numeric_root")
if CLAUDE_PLUGIN_ROOT="$numeric_root" "$WRITE_SCRIPT" \
    --output "$OUT" --repo a/b --repo-unavailable false 2>/dev/null; then
    after=$(stat_mtime "$numeric_root")
    if [[ "$after" -gt "$before" ]]; then
        pass
    else
        fail "F.1 numeric CLAUDE_PLUGIN_ROOT mtime was not refreshed (before=$before after=$after)"
    fi
else
    fail "F.1 numeric CLAUDE_PLUGIN_ROOT writer invocation failed"
fi

non_numeric_root="$TMPDIR_TEST/cache/dev-checkout"
mkdir -p "$non_numeric_root"
touch -t 200001010001 -- "$non_numeric_root"
before=$(stat_mtime "$non_numeric_root")
if CLAUDE_PLUGIN_ROOT="$non_numeric_root" "$WRITE_SCRIPT" \
    --output "$OUT" --repo a/b --repo-unavailable false 2>/dev/null; then
    after=$(stat_mtime "$non_numeric_root")
    if [[ "$after" -eq "$before" ]]; then
        pass
    else
        fail "F.2 non-numeric CLAUDE_PLUGIN_ROOT mtime changed (before=$before after=$after)"
    fi
else
    fail "F.2 non-numeric CLAUDE_PLUGIN_ROOT writer invocation failed"
fi

# ------------------------------------------------------------
# G. session-setup.sh — cache-root mtime touch behavior
# ------------------------------------------------------------

numeric_root="$TMPDIR_TEST/cache/42.5.37"
mkdir -p "$numeric_root"
touch -t 200001010001 -- "$numeric_root"
before=$(stat_mtime "$numeric_root")
if CLAUDE_PLUGIN_ROOT="$numeric_root" "$SESSION_SETUP_SCRIPT" \
    --prefix test-session-env-roundtrip \
    --skip-preflight \
    --skip-repo-check >/dev/null 2>/dev/null; then
    after=$(stat_mtime "$numeric_root")
    if [[ "$after" -gt "$before" ]]; then
        pass
    else
        fail "G.1 numeric CLAUDE_PLUGIN_ROOT mtime was not refreshed by session-setup (before=$before after=$after)"
    fi
else
    fail "G.1 numeric CLAUDE_PLUGIN_ROOT session-setup invocation failed"
fi

non_numeric_root="$TMPDIR_TEST/cache/dev-session-setup"
mkdir -p "$non_numeric_root"
touch -t 200001010001 -- "$non_numeric_root"
before=$(stat_mtime "$non_numeric_root")
if CLAUDE_PLUGIN_ROOT="$non_numeric_root" "$SESSION_SETUP_SCRIPT" \
    --prefix test-session-env-roundtrip \
    --skip-preflight \
    --skip-repo-check >/dev/null 2>/dev/null; then
    after=$(stat_mtime "$non_numeric_root")
    if [[ "$after" -eq "$before" ]]; then
        pass
    else
        fail "G.2 non-numeric CLAUDE_PLUGIN_ROOT mtime changed via session-setup (before=$before after=$after)"
    fi
else
    fail "G.2 non-numeric CLAUDE_PLUGIN_ROOT session-setup invocation failed"
fi

# ------------------------------------------------------------
# H. write-design-current-env.sh — cache-root mtime touch behavior
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
    fail "H.0a CLAUDE_PLUGIN_ROOT with space accepted by write-design-current-env"
else
    assert_contains "H.0a error message" "Invalid CLAUDE_PLUGIN_ROOT" "$err"
fi

if err=$(HOME="$design_home" CLAUDE_PLUGIN_ROOT="relative/plugin-root" "$WRITE_DESIGN_CURRENT_ENV_SCRIPT" \
    --output "$design_out" \
    --design-tmpdir "$design_tmpdir" \
    --session-id test-design-roundtrip \
    --claude-pid 7654321 2>&1); then
    fail "H.0b relative CLAUDE_PLUGIN_ROOT accepted by write-design-current-env"
else
    assert_contains "H.0b error message" "Invalid CLAUDE_PLUGIN_ROOT" "$err"
fi

numeric_root="$TMPDIR_TEST/cache/42.5.38"
mkdir -p "$numeric_root"
touch -t 200001010001 -- "$numeric_root"
before=$(stat_mtime "$numeric_root")
if HOME="$design_home" CLAUDE_PLUGIN_ROOT="$numeric_root" "$WRITE_DESIGN_CURRENT_ENV_SCRIPT" \
    --output "$design_out" \
    --design-tmpdir "$design_tmpdir" \
    --session-id test-design-roundtrip \
    --claude-pid 7654321 >/dev/null 2>/dev/null; then
    after=$(stat_mtime "$numeric_root")
    if [[ "$after" -gt "$before" ]]; then
        pass
    else
        fail "H.1 numeric CLAUDE_PLUGIN_ROOT mtime was not refreshed by write-design-current-env (before=$before after=$after)"
    fi
else
    fail "H.1 numeric CLAUDE_PLUGIN_ROOT write-design-current-env invocation failed"
fi

non_numeric_root="$TMPDIR_TEST/cache/dev-design"
mkdir -p "$non_numeric_root"
touch -t 200001010001 -- "$non_numeric_root"
before=$(stat_mtime "$non_numeric_root")
if HOME="$design_home" CLAUDE_PLUGIN_ROOT="$non_numeric_root" "$WRITE_DESIGN_CURRENT_ENV_SCRIPT" \
    --output "$design_out" \
    --design-tmpdir "$design_tmpdir" \
    --session-id test-design-roundtrip \
    --claude-pid 7654321 >/dev/null 2>/dev/null; then
    after=$(stat_mtime "$non_numeric_root")
    if [[ "$after" -eq "$before" ]]; then
        pass
    else
        fail "H.2 non-numeric CLAUDE_PLUGIN_ROOT mtime changed via write-design-current-env (before=$before after=$after)"
    fi
else
    fail "H.2 non-numeric CLAUDE_PLUGIN_ROOT write-design-current-env invocation failed"
fi

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

echo "test-session-env-roundtrip.sh: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
