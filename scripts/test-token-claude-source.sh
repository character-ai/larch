#!/usr/bin/env bash
# test-token-claude-source.sh — offline regression harness for token-claude-source.sh.
#
# Covers the LARCH_CLAUDE_SOURCE_FILE snapshot replay short-circuit (the
# durable fix for concurrent-session attribution) plus the live mtime /
# session-id resolver. Live-resolver tests run inside a fresh git repo with
# a fake $HOME so ~/.claude/projects/<encoded>/ is under the harness's
# tmpdir.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/token-claude-source.sh"
PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1" >&2; FAIL=$((FAIL + 1)); }
contains() {
    case "$3" in
        *"$2"*) pass ;;
        *) fail "$1 missing '$2': $3" ;;
    esac
}
not_contains() {
    case "$3" in
        *"$2"*) fail "$1 should not contain '$2': $3" ;;
        *) pass ;;
    esac
}

ROOT="${TMPDIR:-/tmp}"
TMP=$(mktemp -d "$ROOT/test-token-claude-source.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

# --- Snapshot replay (short-circuits before git/HOME) -------------------------

# Test 1: fresh snapshot with all 3 keys + an existing TRANSCRIPT_PATH replays
# verbatim. The script SHOULD NOT consult the live resolver — even when run
# from outside any git repo, the snapshot wins.
SNAP_TRANSCRIPT="$TMP/snap-transcript.jsonl"
: > "$SNAP_TRANSCRIPT"
SNAP="$TMP/snap.env"
cat > "$SNAP" <<EOF
TRANSCRIPT_PATH=$SNAP_TRANSCRIPT
SESSION_DIR=$TMP/session-dir
SESSION_UUID=abcd-1234
EOF
out=$(cd "$TMP" && LARCH_CLAUDE_SOURCE_FILE="$SNAP" "$SCRIPT")
contains "snap transcript" "TRANSCRIPT_PATH=$SNAP_TRANSCRIPT" "$out"
contains "snap session_dir" "SESSION_DIR=$TMP/session-dir" "$out"
contains "snap session_uuid" "SESSION_UUID=abcd-1234" "$out"

# Test 2: snapshot pointing at non-existent TRANSCRIPT_PATH falls through to
# live resolver. Documented behavior — a corrupted snapshot must not lock
# callers out.
SNAP_BAD="$TMP/snap-bad.env"
cat > "$SNAP_BAD" <<EOF
TRANSCRIPT_PATH=$TMP/does-not-exist.jsonl
SESSION_DIR=$TMP/dummy
SESSION_UUID=dummy-uuid
EOF
# Run from outside any git repo so the live resolver fails cleanly with
# STATUS=unavailable. The point of this test is that the stale TRANSCRIPT_PATH
# is NOT replayed, not what the live resolver does on fall-through.
out=$(cd "$TMP" && LARCH_CLAUDE_SOURCE_FILE="$SNAP_BAD" "$SCRIPT" 2>&1) || true
not_contains "stale snapshot not replayed" "TRANSCRIPT_PATH=$TMP/does-not-exist.jsonl" "$out"

# Test 3: snapshot file with garbage / missing TRANSCRIPT_PATH falls through
# silently — no error from the env-parse loop. As above, run from outside a
# git repo so the live resolver's fail path is the predictable outcome.
SNAP_GARBAGE="$TMP/snap-garbage.env"
printf 'random text\n  not key=value\n' > "$SNAP_GARBAGE"
out=$(cd "$TMP" && LARCH_CLAUDE_SOURCE_FILE="$SNAP_GARBAGE" "$SCRIPT" 2>&1) || true
not_contains "garbage not echoed" "random text" "$out"

# Test 4: missing snapshot file (env var set but file unreadable) silently
# falls through.
out=$(cd "$TMP" && LARCH_CLAUDE_SOURCE_FILE="$TMP/does-not-exist.env" "$SCRIPT" 2>&1) || true
# Either the live resolver succeeded (TRANSCRIPT_PATH=...) or it failed cleanly
# (STATUS=unavailable). Running from $TMP (not a git repo) deterministically
# trips the unavailable path.
case "$out" in
    *"STATUS=unavailable"*) pass ;;
    *"TRANSCRIPT_PATH="*) pass ;;
    *) fail "missing snapshot file should fall through silently: $out" ;;
esac

# --- Live resolver with fake $HOME / fake git repo ----------------------------

# A non-empty fake repo plus an encoded project dir under the fake HOME mirror
# the script's resolver expectations.
FAKE_HOME="$TMP/home"
mkdir -p "$FAKE_HOME"
FAKE_REPO="$TMP/repo"
mkdir -p "$FAKE_REPO"
( cd "$FAKE_REPO" && git init -q && git config user.email "t@t" && git config user.name "t" )
# token-claude-source.sh canonicalizes via `git rev-parse --show-toplevel` +
# `pwd -P`; on macOS that resolves `/var/folders/...` → `/private/var/...`,
# so derive ENCODED from the canonicalized path the script will see.
FAKE_REPO_REAL=$(cd "$FAKE_REPO" && git rev-parse --show-toplevel)
FAKE_REPO_REAL=$(cd "$FAKE_REPO_REAL" && pwd -P)
ENCODED=$(printf '%s' "$FAKE_REPO_REAL" | sed 's#/#-#g')
PROJECT_DIR="$FAKE_HOME/.claude/projects/$ENCODED"
mkdir -p "$PROJECT_DIR"

# Filename order DELIBERATELY contradicts mtime order so a buggy resolver
# that picked the lexically-last (or lexically-first) file would not
# accidentally satisfy the assertions: T1 lexicographically sorts FIRST
# but is mtime-OLDEST, T2 sorts LAST but is mtime-NEWEST. Only a true
# mtime-newest-wins resolver picks T2 here.
T1="$PROJECT_DIR/zzzz-old-9999.jsonl"
T2="$PROJECT_DIR/aaaa-newer-1111.jsonl"
: > "$T1"
sleep 1
: > "$T2"

# Test 5: newest-by-mtime wins (T2 is newer than T1 by mtime even though T1
# is lexicographically last).
out=$(cd "$FAKE_REPO" && HOME="$FAKE_HOME" "$SCRIPT")
contains "mtime newest transcript" "TRANSCRIPT_PATH=$T2" "$out"
contains "mtime session_uuid" "SESSION_UUID=aaaa-newer-1111" "$out"

# Test 6: LARCH_CLAUDE_SESSION_ID overrides mtime when its name matches a file
# in the project dir.
out=$(cd "$FAKE_REPO" && HOME="$FAKE_HOME" LARCH_CLAUDE_SESSION_ID="zzzz-old-9999" "$SCRIPT")
contains "session-id override picks T1 (mtime-older)" "TRANSCRIPT_PATH=$T1" "$out"

# Test 7: LARCH_CLAUDE_SESSION_ID with bad chars (path traversal attempt) is
# silently skipped — falls back to mtime resolution.
out=$(cd "$FAKE_REPO" && HOME="$FAKE_HOME" LARCH_CLAUDE_SESSION_ID="../escape" "$SCRIPT")
contains "bad session-id falls back to mtime" "TRANSCRIPT_PATH=$T2" "$out"

# Test 8: empty project dir → STATUS=unavailable.
EMPTY_REPO="$TMP/empty-repo"
mkdir -p "$EMPTY_REPO"
( cd "$EMPTY_REPO" && git init -q )
EMPTY_REPO_REAL=$(cd "$EMPTY_REPO" && git rev-parse --show-toplevel)
EMPTY_REPO_REAL=$(cd "$EMPTY_REPO_REAL" && pwd -P)
EMPTY_ENCODED=$(printf '%s' "$EMPTY_REPO_REAL" | sed 's#/#-#g')
mkdir -p "$FAKE_HOME/.claude/projects/$EMPTY_ENCODED"
out=$(cd "$EMPTY_REPO" && HOME="$FAKE_HOME" "$SCRIPT" 2>&1) || true
contains "empty project status" "STATUS=unavailable" "$out"
contains "empty project reason" "no Claude transcript" "$out"

# --- Concurrent-session resolver behavior -------------------------------------

# Test 9: snapshot replay wins even when newer transcripts appear after the
# snapshot was captured. This is the documented fix for concurrent-session
# attribution: a sticky snapshot binds the session to a specific transcript
# regardless of mtime drift caused by other Claude sessions writing under
# the same project dir.
# Lexicographically-MIDDLE name (sorts after T2/aaaa- but before T1/zzzz-),
# but mtime-newest. Only a true mtime resolver picks T3 here.
T3="$PROJECT_DIR/mmmm-newest-3333.jsonl"
sleep 1
: > "$T3"  # T3 is now newest by mtime

# Without snapshot: T3 would win.
out=$(cd "$FAKE_REPO" && HOME="$FAKE_HOME" "$SCRIPT")
contains "without snapshot, newest concurrent wins" "TRANSCRIPT_PATH=$T3" "$out"

# With snapshot pinning T1: T1 wins despite T3 being newer.
SNAP_PIN="$TMP/snap-pin.env"
cat > "$SNAP_PIN" <<EOF
TRANSCRIPT_PATH=$T1
SESSION_DIR=$PROJECT_DIR/zzzz-old-9999
SESSION_UUID=zzzz-old-9999
EOF
out=$(cd "$FAKE_REPO" && HOME="$FAKE_HOME" LARCH_CLAUDE_SOURCE_FILE="$SNAP_PIN" "$SCRIPT")
contains "snapshot pinning beats newer concurrent" "TRANSCRIPT_PATH=$T1" "$out"
contains "snapshot pinning carries pinned uuid" "SESSION_UUID=zzzz-old-9999" "$out"

total=$((PASS + FAIL))
if (( FAIL == 0 )); then
    echo "PASS: test-token-claude-source.sh — $PASS/$total assertions"
else
    echo "FAIL: test-token-claude-source.sh — $FAIL/$total assertions failed" >&2
    exit 1
fi
