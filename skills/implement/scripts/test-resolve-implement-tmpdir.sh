#!/usr/bin/env bash

set -euo pipefail

# Offline harness: resolve_implement_tmpdir binds the session whose
# .larch-keepalive CLONE_PATH matches the hook cwd when multiple implement
# session roots exist (concurrent worktrees).

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
LIB="$REPO_ROOT/skills/implement/scripts/lib-resolve-implement-tmpdir.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-resolve-implement-tmpdir.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

FRESH_TS='209901010000'

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

# shellcheck source=skills/implement/scripts/lib-resolve-implement-tmpdir.sh
source "$LIB"

WORKTREE_A="$TMP/worktree-a"
WORKTREE_B="$TMP/worktree-b"
mkdir -p "$WORKTREE_A" "$WORKTREE_B"

SESSIONS="$TMP/cache/larch/sessions"
mkdir -p "$SESSIONS"

DIR_A="$SESSIONS/claude-implement-worktree-a"
mkdir -p "$DIR_A/design-export"
printf 'export PLAN=1\n' > "$DIR_A/design-export/manifest.env"
touch -t "$FRESH_TS" -- "$DIR_A/design-export/manifest.env"
printf '# larch session identity (hook routing)\nCLONE_PATH=%s\nSESSION_ID=sid-a\n' \
    "$WORKTREE_A" > "$DIR_A/.larch-keepalive"

DIR_B="$SESSIONS/claude-implement-worktree-b"
mkdir -p "$DIR_B/design-export"
printf 'export PLAN=1\n' > "$DIR_B/design-export/manifest.env"
touch -t "$FRESH_TS" -- "$DIR_B/design-export/manifest.env"
printf '# larch session identity (hook routing)\nCLONE_PATH=%s\nSESSION_ID=sid-b\n' \
    "$WORKTREE_B" > "$DIR_B/.larch-keepalive"

resolve_for_cwd() {
    env -u LARCH_TOKEN_SESSION_ID \
        XDG_CACHE_HOME="$TMP/cache" \
        HOME="$TMP/home" \
        bash -c "source \"\$1\"; resolve_implement_tmpdir \"\$2\"" _ "$LIB" "$1"
}

resolve_for_cwd_with_session() {
    env LARCH_TOKEN_SESSION_ID="$2" \
        XDG_CACHE_HOME="$TMP/cache" \
        HOME="$TMP/home" \
        bash -c "source \"\$1\"; resolve_implement_tmpdir \"\$2\"" _ "$LIB" "$1"
}

resolved=$(resolve_for_cwd "$WORKTREE_A")
[[ "$resolved" == "$DIR_A" ]] || fail "expected worktree A session dir, got [$resolved]"

resolved=$(resolve_for_cwd "$WORKTREE_B")
[[ "$resolved" == "$DIR_B" ]] || fail "expected worktree B session dir, got [$resolved]"

# B has a fresher manifest, but cwd binding must not cross-route to B when asking for A.
resolved=$(resolve_for_cwd "$WORKTREE_A")
[[ "$resolved" != "$DIR_B" ]] || fail "worktree A cwd must not resolve to worktree B session"

DIR_C="$SESSIONS/claude-implement-worktree-a-alt"
mkdir -p "$DIR_C/design-export"
printf 'export PLAN=1\n' > "$DIR_C/design-export/manifest.env"
touch -t "$FRESH_TS" -- "$DIR_C/design-export/manifest.env"
printf '# larch session identity (hook routing)\nCLONE_PATH=%s\nSESSION_ID=sid-c\n' \
    "$WORKTREE_A" > "$DIR_C/.larch-keepalive"

resolved=$(resolve_for_cwd_with_session "$WORKTREE_A" "sid-a")
[[ "$resolved" == "$DIR_A" ]] || fail "expected sid-a session dir, got [$resolved]"
[[ "$resolved" != "$DIR_C" ]] || fail "sid-a must not resolve to sid-c session with same CLONE_PATH"

resolved=$(resolve_for_cwd_with_session "$WORKTREE_A" "sid-c")
[[ "$resolved" == "$DIR_C" ]] || fail "expected sid-c session dir, got [$resolved]"

printf 'PASS: test-resolve-implement-tmpdir.sh\n'
