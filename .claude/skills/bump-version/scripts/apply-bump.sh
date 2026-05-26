#!/usr/bin/env bash
# apply-bump.sh — Apply a computed semver bump to .claude-plugin/plugin.json.
#
# Contract:
#   - FIRST: verify working tree is clean (fails on any staged or unstaged changes).
#   - Validate .claude-plugin/plugin.json with jq.
#   - Back up plugin.json.
#   - Rewrite .version field atomically via jq + mv.
#   - git add, fetch origin/main, and fail closed with rollback if origin/main
#     already publishes the requested version or is ahead of it.
#   - Commit with message "Bump version to <new-version>".
#   - Roll back from backup if git commit fails.
#
# Usage:
#   apply-bump.sh --new-version <x.y.z>
#
# Output (stdout):
#   APPLIED=true|false
#   COMMIT_SHA=<sha>             (if APPLIED=true)
#   ERROR=<message>              (if APPLIED=false)
#
# Exit codes: 0 on success, 1 on invalid args / validation / dirty worktree /
#   origin/main same-version or regression guard failures / commit failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LARCH_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$LARCH_PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

# fail MESSAGE — emit APPLIED=false / ERROR=MESSAGE on stdout and exit 1.
# Used for all non-rollback failure paths so callers see a consistent
# machine-parseable contract on stdout.
fail() {
  emit_kv APPLIED false
  emit_kv ERROR "$1"
  exit 1
}

semver_lt() {
  local a_maj a_min a_pat b_maj b_min b_pat
  IFS='.' read -r a_maj a_min a_pat <<< "$1"
  IFS='.' read -r b_maj b_min b_pat <<< "$2"
  if [[ $a_maj -lt $b_maj ]]; then return 0; fi
  if [[ $a_maj -gt $b_maj ]]; then return 1; fi
  if [[ $a_min -lt $b_min ]]; then return 0; fi
  if [[ $a_min -gt $b_min ]]; then return 1; fi
  if [[ $a_pat -lt $b_pat ]]; then return 0; fi
  return 1
}

# Derives MAJOR/MINOR/PATCH from an (original_current, initial_target) pair.
_infer_bump_type() {
  local c_maj c_min n_maj n_min
  IFS='.' read -r c_maj c_min _ <<< "$1"
  IFS='.' read -r n_maj n_min _ <<< "$2"
  if [[ $n_maj -gt $c_maj ]]; then printf '%s\n' MAJOR
  elif [[ $n_min -gt $c_min ]]; then printf '%s\n' MINOR
  else printf '%s\n' PATCH
  fi
}

# Applies a bump type to a base version and prints the result.
_apply_bump_type() {
  local maj min pat
  IFS='.' read -r maj min pat <<< "$1"
  case "$2" in
    MAJOR) printf '%s\n' "$((maj+1)).0.0" ;;
    MINOR) printf '%s\n' "${maj}.$((min+1)).0" ;;
    *)     printf '%s\n' "${maj}.${min}.$((pat+1))" ;;
  esac
}

NEW_VERSION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --new-version)
      if [[ $# -lt 2 || -z "${2:-}" ]]; then
        fail "Missing value for --new-version"
      fi
      NEW_VERSION="$2"
      shift 2
      ;;
    *) fail "Unknown argument: $1" ;;
  esac
done

if [[ -z "$NEW_VERSION" ]]; then
  fail "Missing required argument: --new-version"
fi

if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  fail "--new-version '$NEW_VERSION' is not semver (expected X.Y.Z)"
fi

PLUGIN_JSON="$PWD/.claude-plugin/plugin.json"
BACKUP="$PLUGIN_JSON.bump-backup"

rollback_before_commit() {
  mv "$BACKUP" "$PLUGIN_JSON"
  git reset HEAD "$PLUGIN_JSON" >/dev/null 2>&1 || true
}

# Step 1 (FIRST): Verify clean working tree.
# This MUST run before any mutation so the script can't trip over its own write.
# `git status --porcelain` covers tracked changes (staged and unstaged) AND
# untracked files — unlike `git diff-index --quiet HEAD --` which silently
# ignores untracked entries.
#
# Known-larch-internal untracked artifacts (.launcher-stderr sidecars from the
# review dispatch, *.redacted.log from relevant-checks) are tolerated: they do
# not affect the bump commit and appear when a /implement run reaches Step 8
# without fully cleaning up review artifacts.  Any other dirty entry (staged,
# tracked-modified, or truly foreign untracked files) still fails immediately.

# Pre-check: detect unmerged paths from an in-progress merge or rebase before
# the generic dirty-tree check so callers receive a distinct exit code (4)
# instead of the generic exit-1 "not clean" error. Unmerged-path codes in
# porcelain format:
# UU = both modified, AA = both added, DD = both deleted, AU/UA/DU/UD = partial.
_unmerged=$(git status --porcelain 2>/dev/null | grep -E '^(UU|AA|DD|AU|UA|DU|UD) ' || true)
if [[ -n "$_unmerged" ]]; then
  _unmerged_files=$(printf '%s\n' "$_unmerged" | awk '{print $2}' | tr '\n' ',' | sed 's/,$//')
  emit_kv APPLIED false
  emit_kv ERROR "unmerged paths present: $_unmerged_files. Resolve conflicts from the in-progress merge or rebase (git merge --continue/--abort or git rebase --continue/--abort) before bumping."
  exit 4
fi

_raw_status=$(git status --porcelain 2>/dev/null)
if [[ -n "$_raw_status" ]]; then
  _non_internal=$(printf '%s\n' "$_raw_status" \
    | grep -v '^?? .*\.launcher-stderr$' \
    | grep -v '^?? .*\.redacted\.log$' \
    || true)
  if [[ -n "$_non_internal" ]]; then
    fail "Working tree is not clean (staged, unstaged, or untracked changes present); refusing to bump version. Mid-/implement run: check tracking issue Execution Issues section or \$IMPLEMENT_TMPDIR/execution-issues.md for phantom file warnings. Otherwise: commit, stash, or clean them first."
  fi
  # Only larch-internal artifacts present; log and tolerate.
  _internal_list=$(printf '%s\n' "$_raw_status" | awk '{print $2}' | tr '\n' ' ' | sed 's/ $//')
  printf 'WARN: larch-internal untracked artifacts present (tolerated before bump): %s\n' "$_internal_list" >&2
fi

# Step 2: Validate plugin.json parses.
[[ -f "$PLUGIN_JSON" ]] || fail "$PLUGIN_JSON not found"
jq empty "$PLUGIN_JSON" 2>/dev/null || fail "$PLUGIN_JSON is not valid JSON"
ORIGINAL_CURRENT_VERSION=$(jq -r '.version // empty' "$PLUGIN_JSON")
if [[ ! "$ORIGINAL_CURRENT_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  fail "plugin.json version is not strict semver X.Y.Z (got: '${ORIGINAL_CURRENT_VERSION:-}')"
fi

# _backup_rewrite_stage: back up, atomically rewrite plugin.json to $NEW_VERSION,
# and stage the file. Calls fail() (exit 1) on jq rewrite error.
_backup_rewrite_stage() {
  cp "$PLUGIN_JSON" "$BACKUP"
  local _tmp="$PLUGIN_JSON.tmp.$$"
  if ! jq --arg v "$NEW_VERSION" '.version = $v' "$PLUGIN_JSON" > "$_tmp"; then
    rm -f "$_tmp" "$BACKUP"
    fail "jq rewrite failed"
  fi
  mv "$_tmp" "$PLUGIN_JSON"
  git add "$PLUGIN_JSON"
}

# Steps 3–5: backup, rewrite, stage, then fetch-and-verify in a retry loop.
# On a same-version or version-regression collision, silently re-classify and
# retry up to _max_retries times before bailing loudly.
INITIAL_NEW_VERSION="$NEW_VERSION"
_retry_count=0
_max_retries=10

_backup_rewrite_stage

while true; do
  if ! git fetch origin main --quiet 2>/dev/null; then
    rollback_before_commit
    fail "git fetch origin main failed; cannot verify origin/main version guards"
  fi

  ORIGIN_VERSION=$(git show origin/main:.claude-plugin/plugin.json 2>/dev/null | jq -r -e '.version // empty' 2>/dev/null || echo "")
  if [[ ! "$ORIGIN_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    rollback_before_commit
    fail "could not parse origin/main published version"
  fi

  if [[ "$ORIGIN_VERSION" == "$NEW_VERSION" ]] || semver_lt "$NEW_VERSION" "$ORIGIN_VERSION"; then
    rollback_before_commit
    if [[ $_retry_count -ge $_max_retries ]]; then
      fail "origin/main bump race: could not land version after $_max_retries retries (last origin/main=$ORIGIN_VERSION)"
    fi
    _bump_type=$(_infer_bump_type "$ORIGINAL_CURRENT_VERSION" "$INITIAL_NEW_VERSION")
    NEW_VERSION=$(_apply_bump_type "$ORIGIN_VERSION" "$_bump_type")
    emit_breadcrumb --category=retry "apply-bump: retry $((_retry_count+1))/$_max_retries origin/main=$ORIGIN_VERSION new-version=$NEW_VERSION"
    _retry_count=$((_retry_count+1))
    _backup_rewrite_stage
    continue
  fi
  break
done

COMMIT_MSG="Bump version to $NEW_VERSION"
if git commit -m "$COMMIT_MSG" --quiet; then
  # Success — remove backup, emit result.
  # No larch-log-flush.sh tail-call here: the rebase+re-bump machinery
  # (drop-bump-commit.sh) relies on the bump commit remaining at HEAD.
  rm -f "$BACKUP"
  COMMIT_SHA=$(git rev-parse HEAD)
  emit_kv APPLIED true
  emit_kv COMMIT_SHA "$COMMIT_SHA"
  exit 0
fi

# Step 6: Rollback on commit failure.
# Restore from backup, unstage the file.
mv "$BACKUP" "$PLUGIN_JSON"
git reset HEAD "$PLUGIN_JSON" >/dev/null 2>&1 || true
emit_kv APPLIED false
emit_kv ERROR "git commit failed; rolled back $PLUGIN_JSON from backup"
exit 1
