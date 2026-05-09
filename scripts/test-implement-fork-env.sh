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

# Happy path with explicit --tmpdir (test-only override): assert all stdout
# keys are emitted including the new BOOTSTRAP_TMPDIR + CALLER_ENV_PATH keys
# (Round 1 FINDING_1 fix).
repo="$TMPROOT/repo"
git init "$repo" >/dev/null
git -C "$repo" remote add origin git@github.com:fork-owner/fork-repo.git
git -C "$repo" remote add upstream https://github.com/upstream-owner/upstream-repo.git

out=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SCRIPT" --tmpdir "$TMPROOT/session")
grep -Fxq "BOOTSTRAP_TMPDIR=$TMPROOT/session" <<<"$out" \
    || fail "missing BOOTSTRAP_TMPDIR stdout (or path drifted)"
grep -Fxq "CALLER_ENV_PATH=$TMPROOT/session/caller-env.sh" <<<"$out" \
    || fail "missing CALLER_ENV_PATH stdout (or path drifted)"
grep -Fxq 'FORK_REPO=fork-owner/fork-repo' <<<"$out" || fail "missing FORK_REPO stdout"
grep -Fxq 'UPSTREAM_REPO=upstream-owner/upstream-repo' <<<"$out" || fail "missing UPSTREAM_REPO stdout"
grep -Fxq 'FORK_OWNER=fork-owner' <<<"$out" || fail "missing FORK_OWNER stdout"
grep -Fxq 'FORKED_TARGET=true' <<<"$out" || fail "missing FORKED_TARGET stdout"
[[ "$(cat "$TMPROOT/session/caller-env.sh")" == "REPO=fork-owner/fork-repo" ]] \
    || fail "caller-env should contain only fork REPO"

# Happy path with self-allocated bootstrap (production caller shape):
# omit --tmpdir entirely. The helper picks its own mktemp path under
# ${TMPDIR:-/tmp}/larch-fork-bootstrap.XXXXXX. Assert BOOTSTRAP_TMPDIR is
# emitted, the path exists, and caller-env.sh sits inside it.
out2=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SCRIPT")
bootstrap=$(grep -E '^BOOTSTRAP_TMPDIR=' <<<"$out2" | head -1 | cut -d= -f2-)
[[ -n "$bootstrap" ]] || fail "self-allocated bootstrap: BOOTSTRAP_TMPDIR empty"
[[ -d "$bootstrap" ]] || fail "self-allocated bootstrap: directory does not exist"
[[ -f "$bootstrap/caller-env.sh" ]] || fail "self-allocated bootstrap: caller-env.sh missing"
grep -Fxq "CALLER_ENV_PATH=$bootstrap/caller-env.sh" <<<"$out2" \
    || fail "self-allocated bootstrap: CALLER_ENV_PATH does not match BOOTSTRAP_TMPDIR"
[[ "$(cat "$bootstrap/caller-env.sh")" == "REPO=fork-owner/fork-repo" ]] \
    || fail "self-allocated bootstrap: caller-env content drift"
rm -rf "$bootstrap"

# Missing upstream remote: exit 1 with explicit error referencing the
# documented setup walkthrough (Round 1 FINDING_3 — no slash-command).
missing="$TMPROOT/missing-upstream"
git init "$missing" >/dev/null
git -C "$missing" remote add origin git@github.com:fork-owner/fork-repo.git
set +e
(cd "$missing" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SCRIPT" --tmpdir "$TMPROOT/missing-session") >"$TMPROOT/missing.out" 2>"$TMPROOT/missing.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "missing upstream should fail"
grep -Fq -- '--forked requires the clone' "$TMPROOT/missing.err" \
    || fail "missing-upstream error text drifted"
grep -Fq 'docs/installation-and-setup.md' "$TMPROOT/missing.err" \
    || fail "missing-upstream error should point at docs/installation-and-setup.md (FINDING_3)"
grep -Fq '/set-up-forked-open-source-repo' "$TMPROOT/missing.err" \
    && fail "missing-upstream error must NOT reference dead /set-up-forked-open-source-repo slash command (FINDING_3)"
grep -Fq 'git remote add upstream' "$TMPROOT/missing.err" \
    || fail "missing-upstream error should show the explicit git remote add upstream contract"

# Bad origin URL (non-github host): github-remote-repo.sh fails parse,
# implement-fork-env.sh propagates non-zero exit.
bad="$TMPROOT/bad-origin"
git init "$bad" >/dev/null
git -C "$bad" remote add origin https://example.com/fork-owner/fork-repo.git
git -C "$bad" remote add upstream https://github.com/upstream-owner/upstream-repo.git
set +e
(cd "$bad" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SCRIPT" --tmpdir "$TMPROOT/bad-session") >"$TMPROOT/bad.out" 2>"$TMPROOT/bad.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "unparseable origin should fail"

# Bad upstream URL (origin is valid GitHub, upstream is non-github):
# the upstream parse must fail too. Pinned per /review reviewer suggestion
# (FINDING_8 was rejected on proportionality, but the symmetric assertion
# is added now since the fork-env contract is being touched anyway).
badup="$TMPROOT/bad-upstream"
git init "$badup" >/dev/null
git -C "$badup" remote add origin git@github.com:fork-owner/fork-repo.git
git -C "$badup" remote add upstream https://example.com/upstream-owner/upstream-repo.git
set +e
(cd "$badup" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SCRIPT" --tmpdir "$TMPROOT/badup-session") >"$TMPROOT/badup.out" 2>"$TMPROOT/badup.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "unparseable upstream (with valid origin) should fail"

echo "PASS: test-implement-fork-env.sh"
