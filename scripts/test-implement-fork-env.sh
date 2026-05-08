#!/usr/bin/env bash
# Regression harness for scripts/implement-fork-env.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/implement-fork-env.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-fork-env.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

repo="$TMPROOT/repo"
git init "$repo" >/dev/null
git -C "$repo" remote add origin git@github.com:fork-owner/fork-repo.git
git -C "$repo" remote add upstream https://github.com/upstream-owner/upstream-repo.git

out=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SCRIPT" --tmpdir "$TMPROOT/session")
grep -Fxq 'FORK_REPO=fork-owner/fork-repo' <<<"$out" || fail "missing FORK_REPO stdout"
grep -Fxq 'UPSTREAM_REPO=upstream-owner/upstream-repo' <<<"$out" || fail "missing UPSTREAM_REPO stdout"
grep -Fxq 'FORK_OWNER=fork-owner' <<<"$out" || fail "missing FORK_OWNER stdout"
grep -Fxq 'FORKED_TARGET=true' <<<"$out" || fail "missing FORKED_TARGET stdout"
grep -Fxq 'SLACK_ENABLED=false' <<<"$out" || fail "missing SLACK_ENABLED stdout"
[[ "$(cat "$TMPROOT/session/caller-env.sh")" == "REPO=fork-owner/fork-repo" ]] \
    || fail "caller-env should contain only fork REPO"

missing="$TMPROOT/missing-upstream"
git init "$missing" >/dev/null
git -C "$missing" remote add origin git@github.com:fork-owner/fork-repo.git
set +e
(cd "$missing" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SCRIPT" --tmpdir "$TMPROOT/missing-session") >"$TMPROOT/missing.out" 2>"$TMPROOT/missing.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "missing upstream should fail"
grep -Fq -- '--forked requires the clone to be configured' "$TMPROOT/missing.err" \
    || fail "missing upstream error text drifted"

bad="$TMPROOT/bad-origin"
git init "$bad" >/dev/null
git -C "$bad" remote add origin https://example.com/fork-owner/fork-repo.git
git -C "$bad" remote add upstream https://github.com/upstream-owner/upstream-repo.git
set +e
(cd "$bad" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SCRIPT" --tmpdir "$TMPROOT/bad-session") >"$TMPROOT/bad.out" 2>"$TMPROOT/bad.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "unparseable origin should fail"

echo "PASS: test-implement-fork-env.sh"
