#!/usr/bin/env bash
# drop-bump-commit.sh — Drop a "Bump version to X.Y.Z" commit from the branch.
#
# Narrow primitive used by /implement's Rebase + Re-bump Sub-procedure to
# strip a stale version-bump commit before rebasing onto latest main.
# Walks back up to --max-depth commits (default 10) from HEAD looking for
# the most recent bump commit.  Refuses to do anything destructive unless
# ALL of these hold:
#   1. Working tree has no uncommitted changes to tracked files.
#      Untracked files are excluded from this check because the drop
#      operation does not affect them.
#   2. The found commit's subject matches ^Bump version to [0-9]+\.[0-9]+\.[0-9]+$.
#   3. The parent of the found commit exists.
#   4. The found commit touches only allowed bump files (optionally together
#      with CHANGELOG.md), and nothing else.
#
# Guard 4 allowed-file set:
#   - When LARCH_BUMP_FILES is unset: defaults to .claude-plugin/plugin.json
#     (exact two-string equality, byte-identical to pre-configuration behavior).
#   - When LARCH_BUMP_FILES is set: colon-separated list of bump files
#     (replacement semantics — replaces the default, not additive).
#     Membership check: every file in the diff must be in the allowed set.
#     Fail-closed on empty parse.
#   CHANGELOG.md is always allowed (never required) on both paths.
#
# If any check fails, the script prints DROPPED=false and exits 0 (no-op).
# A stderr WARN line explains which guard refused the drop, for callers that
# want to surface it.
#
# Usage:
#   drop-bump-commit.sh [--max-depth N]
#
# Options:
#   --max-depth N   Walk at most N commits back from HEAD (default 10).
#
# Output (stdout, KEY=VALUE):
#   DROPPED=true|false
#   OLD_BUMP_SHA=<sha>   (only when DROPPED=true)
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
MAX_DEPTH=10
while [ "$#" -gt 0 ]; do
    case "$1" in
        --max-depth)
            if [ "$#" -lt 2 ]; then
                larch_err "WARN: --max-depth requires a value"
                emit_kv DROPPED false
                exit 0
            fi
            MAX_DEPTH="$2"
            # Validate numeric
            case "$MAX_DEPTH" in
                ''|*[!0-9]*) larch_err "WARN: --max-depth must be a positive integer"; emit_kv DROPPED false; exit 0 ;;
            esac
            [ "$MAX_DEPTH" -gt 0 ] || { larch_err "WARN: --max-depth must be >= 1"; emit_kv DROPPED false; exit 0; }
            shift 2
            ;;
        *) larch_err "WARN: unknown argument: $1"; emit_kv DROPPED false; exit 0 ;;
    esac
done

# --- Guard 1: clean working tree (tracked files only) ---
# Defense in depth: the drop operation destroys uncommitted changes to TRACKED
# files. Untracked files are unaffected, so they are excluded from this check
# via --untracked-files=no. This avoids spurious DROPPED=false when larch-log
# writes are pending in the worktree (untracked until the next commit call).
if [[ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]]; then
    larch_err "WARN: worktree has uncommitted tracked changes; refusing to drop bump commit"
    emit_kv DROPPED false
    exit 0
fi

# --- Guard 2: walk back up to MAX_DEPTH looking for the most recent bump commit ---
FOUND_AT=-1
_depth=0
while [ "$_depth" -lt "$MAX_DEPTH" ]; do
    _ref="HEAD~$_depth"
    # Verify this ref exists before querying its subject.
    if ! git rev-parse --verify "$_ref" >/dev/null 2>&1; then
        break
    fi
    _subj=$(git log -1 --format=%s "$_ref" 2>/dev/null || true)
    if [[ "$_subj" =~ ^Bump\ version\ to\ [0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        FOUND_AT="$_depth"
        break
    fi
    _depth=$(( _depth + 1 ))
done

if [ "$FOUND_AT" -lt 0 ]; then
    larch_err "WARN: no bump commit found within $MAX_DEPTH commits of HEAD; not dropping"
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

# --- Guard 4: the found commit must touch only allowed bump files ---
CHANGED_FILES=$(git diff --name-only "$_parent_ref" "HEAD~$FOUND_AT" 2>/dev/null | LC_ALL=C sort)

if [[ -n "${LARCH_BUMP_FILES+x}" ]]; then
    # Custom path: LARCH_BUMP_FILES is set (replacement semantics).
    # Parse colon-separated list, strip whitespace, skip empty segments.
    ALLOWED_SET=()
    IFS=':' read -ra _segments <<< "$LARCH_BUMP_FILES" || true
    for _seg in "${_segments[@]+"${_segments[@]}"}"; do
        _trimmed="${_seg#"${_seg%%[![:space:]]*}"}"
        _trimmed="${_trimmed%"${_trimmed##*[![:space:]]}"}"
        [[ -n "$_trimmed" ]] && ALLOWED_SET+=("$_trimmed")
    done
    if [[ ${#ALLOWED_SET[@]} -eq 0 ]]; then
        larch_err "WARN: LARCH_BUMP_FILES is set but empty after parsing; refusing to drop (fail-closed)"
        emit_kv DROPPED false
        exit 0
    fi
    # CHANGELOG.md is always allowed (never required).
    ALLOWED_SET+=("CHANGELOG.md")

    # Membership check: every changed file must be in the allowed set,
    # AND at least one configured bump file (not CHANGELOG.md) must be present.
    ALLOWED_FAILED=false
    BUMP_FILE_FOUND=false
    while IFS= read -r file; do
        [[ -z "$file" ]] && continue
        FOUND=false
        for allowed in "${ALLOWED_SET[@]}"; do
            if [[ "$file" == "$allowed" ]]; then
                FOUND=true
                [[ "$file" != "CHANGELOG.md" ]] && BUMP_FILE_FOUND=true
                break
            fi
        done
        if [[ "$FOUND" != "true" ]]; then
            ALLOWED_FAILED=true
            break
        fi
    done <<< "$CHANGED_FILES"

    if [[ "$ALLOWED_FAILED" == "true" ]]; then
        larch_err "WARN: found commit at HEAD~$FOUND_AT matches bump pattern but touches unexpected files (changed: $CHANGED_FILES); refusing to drop"
        emit_kv DROPPED false
        exit 0
    fi

    if [[ "$BUMP_FILE_FOUND" != "true" ]]; then
        larch_err "WARN: found commit at HEAD~$FOUND_AT matches bump pattern but touches no configured bump files; refusing to drop (fail-closed)"
        emit_kv DROPPED false
        exit 0
    fi
else
    # Default path: exact two-string equality (byte-identical to pre-configuration behavior).
    # ALLOWED_* constants must match `sort`'s ASCII byte ordering (forced above via LC_ALL=C):
    # '.' (0x2E) sorts before 'C' (0x43), so '.claude-plugin/plugin.json' comes before 'CHANGELOG.md'.
    ALLOWED_ONE=".claude-plugin/plugin.json"
    ALLOWED_TWO=$'.claude-plugin/plugin.json\nCHANGELOG.md'
    if [[ "$CHANGED_FILES" != "$ALLOWED_ONE" && "$CHANGED_FILES" != "$ALLOWED_TWO" ]]; then
        larch_err "WARN: found commit at HEAD~$FOUND_AT matches bump pattern but touches unexpected files (changed: $CHANGED_FILES); refusing to drop"
        emit_kv DROPPED false
        exit 0
    fi
fi

# --- All guards passed: capture SHA and drop ---
OLD_BUMP_SHA=$(git rev-parse "HEAD~$FOUND_AT")

if [ "$FOUND_AT" -eq 0 ]; then
    # Fast path: bump is at HEAD — use reset --hard (no rebase needed).
    if ! git reset --hard HEAD~1 >/dev/null 2>&1; then
        larch_err "ERROR: git reset --hard HEAD~1 failed"
        exit 1
    fi
else
    # Walk-back path: bump is below HEAD — replay commits above it onto its parent.
    # git rebase --onto <newbase> <upstream>:
    #   newbase  = commit just before the bump (HEAD~(FOUND_AT+1))
    #   upstream = the bump commit itself (HEAD~FOUND_AT)
    # This replays [HEAD~FOUND_AT..HEAD] (exclusive) = the commits above the bump.
    _newbase="HEAD~$(( FOUND_AT + 1 ))"
    _upstream="HEAD~$FOUND_AT"
    if ! GIT_SEQUENCE_EDITOR=true git rebase --onto "$_newbase" "$_upstream" >/dev/null 2>&1; then
        larch_err "ERROR: git rebase --onto $_newbase $_upstream failed; aborting rebase"
        git rebase --abort >/dev/null 2>&1 || true
        exit 1
    fi
fi

emit_kv DROPPED true
emit_kv OLD_BUMP_SHA "$OLD_BUMP_SHA"
exit 0
