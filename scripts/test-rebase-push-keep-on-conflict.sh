#!/usr/bin/env bash
# Regression harness for rebase-push.sh --keep-on-conflict local-only conflicts.
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SCRIPT="$REPO_ROOT/scripts/rebase-push.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

configure_repo() {
  git -C "$1" config user.name "Larch Test"
  git -C "$1" config user.email "larch-test@example.invalid"
}

rebase_in_progress() {
  local repo="$1"
  local git_dir
  git_dir=$(git -C "$repo" rev-parse --git-dir)
  [[ -d "$repo/$git_dir/rebase-merge" || -d "$repo/$git_dir/rebase-apply" ]]
}

setup_conflict_repo() {
  local root="$1"
  local origin="$root/origin.git"
  local seed="$root/seed"
  local work="$root/work"

  mkdir -p "$origin" "$seed" "$work"
  git init --bare "$origin" >/dev/null

  git -C "$seed" init >/dev/null
  configure_repo "$seed"
  git -C "$seed" checkout -b main >/dev/null 2>&1
  printf 'base\n' > "$seed/file.txt"
  git -C "$seed" add file.txt
  git -C "$seed" commit -m "Initial main" >/dev/null
  git -C "$seed" remote add origin "$origin"
  git -C "$seed" push origin main >/dev/null 2>&1
  git -C "$origin" symbolic-ref HEAD refs/heads/main

  git -C "$work" init >/dev/null
  configure_repo "$work"
  git -C "$work" remote add origin "$origin"
  git -C "$work" fetch origin main --quiet
  git -C "$work" checkout -b feature origin/main >/dev/null 2>&1
  printf 'feature\n' > "$work/file.txt"
  git -C "$work" add file.txt
  git -C "$work" commit -m "Feature edit" >/dev/null

  printf 'main\n' > "$seed/file.txt"
  git -C "$seed" add file.txt
  git -C "$seed" commit -m "Main edit" >/dev/null
  git -C "$seed" push origin main >/dev/null 2>&1
}

TMPDIR_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-rebase-keep.XXXXXX")
trap 'rm -rf "$TMPDIR_ROOT"' EXIT

# Baseline: plain --no-push preserves the historical abort-on-conflict behavior.
setup_conflict_repo "$TMPDIR_ROOT/default-abort"
default_repo="$TMPDIR_ROOT/default-abort/work"
set +e
default_output=$(cd "$default_repo" && "$SCRIPT" --no-push 2>"$TMPDIR_ROOT/default.err")
default_rc=$?
set -e
[[ "$default_rc" == "1" ]] || fail "plain --no-push conflict expected exit 1, got $default_rc"
[[ -z "$default_output" ]] || fail "plain --no-push conflict should not emit stdout, got: $default_output"
if rebase_in_progress "$default_repo"; then
  fail "plain --no-push conflict should abort the rebase"
fi

# New behavior: --keep-on-conflict leaves the local-only rebase paused for resolution.
setup_conflict_repo "$TMPDIR_ROOT/keep"
keep_repo="$TMPDIR_ROOT/keep/work"
set +e
keep_output=$(cd "$keep_repo" && "$SCRIPT" --no-push --keep-on-conflict 2>"$TMPDIR_ROOT/keep.err")
keep_rc=$?
set -e
[[ "$keep_rc" == "1" ]] || fail "--keep-on-conflict expected exit 1, got $keep_rc"
[[ "$keep_output" == "CONFLICT_FILES=file.txt" ]] || fail "--keep-on-conflict should emit CONFLICT_FILES=file.txt, got: $keep_output"
if ! rebase_in_progress "$keep_repo"; then
  fail "--keep-on-conflict should leave the rebase in progress"
fi

printf 'main\nfeature\n' > "$keep_repo/file.txt"
git -C "$keep_repo" add file.txt
set +e
continue_output=$(cd "$keep_repo" && "$SCRIPT" --continue --no-push --keep-on-conflict 2>"$TMPDIR_ROOT/continue.err")
continue_rc=$?
set -e
[[ "$continue_rc" == "0" ]] || fail "--continue --no-push --keep-on-conflict expected exit 0, got $continue_rc ($(cat "$TMPDIR_ROOT/continue.err"))"
[[ -z "$continue_output" ]] || fail "--continue --no-push should not emit stdout on success, got: $continue_output"
if rebase_in_progress "$keep_repo"; then
  fail "--continue --no-push should finish the resolved rebase"
fi
if git -C "$keep_repo" ls-remote --exit-code --heads origin feature >/dev/null 2>&1; then
  fail "--continue --no-push unexpectedly pushed the feature branch"
fi
[[ "$(cat "$keep_repo/file.txt")" == $'main\nfeature' ]] || fail "resolved file content was not preserved"

set +e
invalid_output=$("$SCRIPT" --keep-on-conflict 2>"$TMPDIR_ROOT/invalid.err")
invalid_rc=$?
set -e
[[ "$invalid_rc" == "3" ]] || fail "--keep-on-conflict without --no-push expected exit 3, got $invalid_rc"
grep -Fq 'REBASE_ERROR=--keep-on-conflict is only valid with --no-push' "$TMPDIR_ROOT/invalid.err" \
  || fail "--keep-on-conflict invalid usage did not emit the expected REBASE_ERROR"
[[ -z "$invalid_output" ]] || fail "invalid usage should not emit stdout, got: $invalid_output"

echo "PASS: test-rebase-push-keep-on-conflict.sh"
