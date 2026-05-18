#!/usr/bin/env bash
# Regression harness for rebase-push.sh fork-mode lease (issue #2322).
#
# In fork mode, /implement --forked invokes
#   rebase-push.sh --base-remote upstream --base-ref main
# but the topic branch lives on `origin` (the fork), not `upstream`. The lease
# snapshot must use the push remote (the branch's tracking remote, typically
# `origin`), not the base remote, or the resulting --force-with-lease has an
# empty expected OID and the push is rejected.
set -euo pipefail

export LARCH_QUIET_DISABLE=1

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

setup_fork_repo() {
  local root="$1"
  local origin="$root/origin.git"
  local upstream="$root/upstream.git"
  local seed="$root/seed"
  local work="$root/work"

  mkdir -p "$origin" "$upstream" "$seed" "$work"
  git init --bare "$origin" >/dev/null
  git init --bare "$upstream" >/dev/null

  git -C "$seed" init >/dev/null
  configure_repo "$seed"
  git -C "$seed" checkout -b main >/dev/null 2>&1
  printf 'base\n' > "$seed/file.txt"
  git -C "$seed" add file.txt
  git -C "$seed" commit -m "Initial main" >/dev/null
  git -C "$seed" remote add origin "$origin"
  git -C "$seed" remote add upstream "$upstream"
  git -C "$seed" push origin main >/dev/null 2>&1
  git -C "$seed" push upstream main >/dev/null 2>&1
  git -C "$origin" symbolic-ref HEAD refs/heads/main
  git -C "$upstream" symbolic-ref HEAD refs/heads/main

  git -C "$work" init >/dev/null
  configure_repo "$work"
  git -C "$work" remote add origin "$origin"
  git -C "$work" remote add upstream "$upstream"
  git -C "$work" fetch origin main --quiet
  git -C "$work" fetch upstream main --quiet
  git -C "$work" checkout -b feature origin/main >/dev/null 2>&1
  printf 'feature\n' > "$work/feature.txt"
  git -C "$work" add feature.txt
  git -C "$work" commit -m "Feature edit" >/dev/null
  git -C "$work" push --set-upstream origin feature >/dev/null 2>&1
  printf 'feature 2\n' > "$work/feature.txt"
  git -C "$work" add feature.txt
  git -C "$work" commit --amend --no-edit >/dev/null
}

TMPDIR_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-rebase-fork.XXXXXX")
trap 'rm -rf "$TMPDIR_ROOT"' EXIT

# Scenario: fork mode — branch tracking points at origin, but --base-remote
# upstream is passed. Without the fix the lease snapshot reads upstream/feature
# (which does not exist), produces an empty expected OID, and the push is
# rejected by the remote. With the fix the lease snapshot reads origin/feature
# (the branch's tracking remote), captures a valid OID, and the force-push
# succeeds.
setup_fork_repo "$TMPDIR_ROOT/fork"
fork_repo="$TMPDIR_ROOT/fork/work"

set +e
fork_output=$(cd "$fork_repo" && "$SCRIPT" --base-remote upstream --base-ref main 2>"$TMPDIR_ROOT/fork.err")
fork_rc=$?
set -e

[[ "$fork_rc" == "0" ]] \
  || fail "fork-mode rebase-push expected exit 0, got $fork_rc (stderr: $(cat "$TMPDIR_ROOT/fork.err"))"
[[ -z "$fork_output" ]] \
  || fail "fork-mode rebase-push should not emit stdout on success, got: $fork_output"

# Confirm the amended commit reached origin (not upstream).
origin_tip=$(git -C "$fork_repo" rev-parse origin/feature)
local_tip=$(git -C "$fork_repo" rev-parse HEAD)
[[ "$origin_tip" == "$local_tip" ]] \
  || fail "origin/feature ($origin_tip) does not match local HEAD ($local_tip) after rebase-push"

# Confirm upstream/feature was never created — the push must target the fork,
# not the upstream.
if git -C "$fork_repo" --git-dir="$TMPDIR_ROOT/fork/upstream.git" show-ref --verify --quiet refs/heads/feature; then
  fail "upstream remote should not have a feature branch (push targeted the wrong remote)"
fi

echo "PASS: test-rebase-push-fork-mode.sh"
