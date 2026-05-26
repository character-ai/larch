#!/usr/bin/env bash
# drop-changelog-commit.sh — Drop an "Update CHANGELOG for X.Y.Z" commit.
#
# Narrow primitive paired with drop-bump-commit.sh. The Rebase + Re-bump
# Sub-procedure uses it to strip the stale CHANGELOG commit that accompanies a
# dropped bump commit so a subsequent rebase onto a main that also has
# `## [X.Y.Z]` does not deadlock in CHANGELOG.md conflicts (issue #2952 Bug A).
#
# Walks back up to --max-depth commits (default 20) from HEAD looking for the
# most recent commit whose subject is exactly `Update CHANGELOG for <version>`.
# Refuses to do anything destructive unless ALL of these hold:
#   1. Working tree has no uncommitted changes to tracked files.
#      Untracked files are excluded from this check because the drop operation
#      does not affect them.
#   2. The found commit's subject matches ^Update CHANGELOG for <version>$.
#   3. The parent of the found commit exists.
#   4. The found commit touches exactly CHANGELOG.md.
#
# If any check fails, the script prints DROPPED=false and exits 0 (no-op). A
# stderr WARN line explains which guard refused the drop, mirroring the
# drop-bump-commit.sh contract.
#
# Usage:
#   drop-changelog-commit.sh --version X.Y.Z [--max-depth N]
#
# Options:
#   --version X.Y.Z Required. Exact version string to match in the subject.
#                   Must satisfy ^[0-9]+\.[0-9]+\.[0-9]+$.
#   --max-depth N   Walk at most N commits back from HEAD (default 20).
#
# Output (stdout, KEY=VALUE):
#   DROPPED=true|false
#   OLD_CHANGELOG_SHA=<sha>   (only when DROPPED=true)
#
# Exit codes:
#   0 — success, including no-op cases (inspect DROPPED to know what happened)
#   1 — git error during the drop itself (rare)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# Note: not using set -e — we handle errors explicitly so all no-op paths
# exit 0 with DROPPED=false, matching the contract used by callers.

# --- Parse flags ---
MAX_DEPTH=20
VERSION=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --version)
            if [ "$#" -lt 2 ]; then
                larch_err "WARN: --version requires a value"
                emit_kv DROPPED false
                exit 0
            fi
            VERSION="$2"
            shift 2
            ;;
        --max-depth)
            if [ "$#" -lt 2 ]; then
                larch_err "WARN: --max-depth requires a value"
                emit_kv DROPPED false
                exit 0
            fi
            MAX_DEPTH="$2"
            case "$MAX_DEPTH" in
                ''|*[!0-9]*) larch_err "WARN: --max-depth must be a positive integer"; emit_kv DROPPED false; exit 0 ;;
            esac
            [ "$MAX_DEPTH" -gt 0 ] || { larch_err "WARN: --max-depth must be >= 1"; emit_kv DROPPED false; exit 0; }
            shift 2
            ;;
        *) larch_err "WARN: unknown argument: $1"; emit_kv DROPPED false; exit 0 ;;
    esac
done

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    larch_err "WARN: --version must match X.Y.Z; got: $VERSION"
    emit_kv DROPPED false
    exit 0
fi

# --- Guard 1: clean working tree (tracked files only) ---
if [[ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]]; then
    larch_err "WARN: worktree has uncommitted tracked changes; refusing to drop changelog commit"
    emit_kv DROPPED false
    exit 0
fi

# --- Guard 2: walk back up to MAX_DEPTH looking for the matching changelog commit ---
EXPECTED_SUBJECT="Update CHANGELOG for $VERSION"
FOUND_AT=-1
_depth=0
while [ "$_depth" -lt "$MAX_DEPTH" ]; do
    _ref="HEAD~$_depth"
    if ! git rev-parse --verify "$_ref" >/dev/null 2>&1; then
        break
    fi
    _subj=$(git log -1 --format=%s "$_ref" 2>/dev/null || true)
    if [[ "$_subj" == "$EXPECTED_SUBJECT" ]]; then
        FOUND_AT="$_depth"
        break
    fi
    _depth=$(( _depth + 1 ))
done

if [ "$FOUND_AT" -lt 0 ]; then
    larch_err "WARN: no '$EXPECTED_SUBJECT' commit found within $MAX_DEPTH commits of HEAD; not dropping"
    emit_kv DROPPED false
    exit 0
fi

# --- Guard 3: the parent of the found commit must exist ---
_parent_ref="HEAD~$(( FOUND_AT + 1 ))"
if ! git rev-parse --verify "$_parent_ref" >/dev/null 2>&1; then
    larch_err "WARN: ${_parent_ref} does not exist; cannot drop the only commit on the branch"
    emit_kv DROPPED false
    exit 0
fi

# --- Guard 4: the found commit must touch exactly CHANGELOG.md ---
CHANGED_FILES=$(git diff --name-only "$_parent_ref" "HEAD~$FOUND_AT" 2>/dev/null | LC_ALL=C sort)
if [[ "$CHANGED_FILES" != "CHANGELOG.md" ]]; then
    larch_err "WARN: found commit at HEAD~$FOUND_AT matches '$EXPECTED_SUBJECT' but touches unexpected files (changed: $CHANGED_FILES); refusing to drop"
    emit_kv DROPPED false
    exit 0
fi

# --- All guards passed: capture SHA and drop ---
OLD_CHANGELOG_SHA=$(git rev-parse "HEAD~$FOUND_AT")

if [ "$FOUND_AT" -eq 0 ]; then
    if ! git reset --hard HEAD~1 >/dev/null 2>&1; then
        larch_err "ERROR: git reset --hard HEAD~1 failed"
        exit 1
    fi
else
    _newbase="HEAD~$(( FOUND_AT + 1 ))"
    _upstream="HEAD~$FOUND_AT"
    if ! GIT_SEQUENCE_EDITOR=true git rebase --onto "$_newbase" "$_upstream" >/dev/null 2>&1; then
        larch_err "ERROR: git rebase --onto $_newbase $_upstream failed; aborting rebase"
        git rebase --abort >/dev/null 2>&1 || true
        exit 1
    fi
fi

emit_kv DROPPED true
emit_kv OLD_CHANGELOG_SHA "$OLD_CHANGELOG_SHA"
exit 0
