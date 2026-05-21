#!/usr/bin/env bash
# post-design-boundary.sh is deprecated (#2485): stub exits 0, stderr warning only.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
WRAPPER="$REPO_ROOT/skills/implement/scripts/post-design-boundary.sh"
POST_HOOK="$REPO_ROOT/skills/implement/scripts/hook-post-design.sh"
STOP_HOOK="$REPO_ROOT/skills/implement/scripts/hook-stop-fail-close.sh"
SKILL_MD="$REPO_ROOT/skills/implement/SKILL.md"

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -x "$WRAPPER" ]] || fail "post-design-boundary.sh missing"
[[ -x "$POST_HOOK" ]] || fail "hook-post-design.sh missing"
[[ -x "$STOP_HOOK" ]] || fail "hook-stop-fail-close.sh missing"

grep -Fq 'deprecated no-op (issue #2485)' "$WRAPPER" \
    || fail "wrapper missing deprecation marker"

grep -Fq '(removed — see issue #2485' "$SKILL_MD" \
    || fail "SKILL.md missing NEVER #12 placeholder"

TMPROOT=$(mktemp -d)
trap 'rm -rf "$TMPROOT"' EXIT

TMP="$TMPROOT/impl"
mkdir -p "$TMP/design-export"
: > "$TMP/design-export/manifest.env"

# Stub: stderr warning, stdout empty-ish, no boundary sentinel, exit 0.
set +e
ERR_OUT=$(CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" \
    --implement-tmpdir "$TMP" \
    --session-env "$TMP/session-env.sh" \
    --design-only false \
    --hook-mode false 2>&1)
RC=$?
set -e
[[ "$RC" -eq 0 ]] || fail "wrapper exit $RC"
printf '%s\n' "$ERR_OUT" | grep -Fq 'deprecated no-op' \
    || fail "stderr missing deprecation text"
[[ ! -f "$TMP/.boundary-gate-passed" ]] || fail "stub must not write .boundary-gate-passed"

# Stop hook: manifest present without boundary sentinel must NOT block (#2485).
STOP_CACHE="$TMPROOT/stop-cache"
STOP_CWD="$TMPROOT/stop-cwd"
mkdir -p "$STOP_CWD"
printf 'CLONE_PATH=%s\n' "$STOP_CWD" > "$TMP/.larch-keepalive"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$STOP_CWD" \
    | XDG_CACHE_HOME="$STOP_CACHE" bash "$STOP_HOOK")
[[ -z "$OUT" ]] || fail "Stop hook should not block on manifest without boundary: $OUT"

# PostToolUse hook: design skill resolves tmpdir — exit 0 (no jq hookSpecificOutput required).
GIT="$TMPROOT/gitx"
mkdir -p "$GIT"
git -C "$GIT" init -q
git -C "$GIT" checkout -q -b t
HOOK_JSON="$TMPROOT/hook.json"
printf '{"tool_name":"Skill","tool_input":{"skill":"design"},"cwd":"%s","session_id":"sid-1"}' "$STOP_CWD" \
    > "$HOOK_JSON"
HOOK_OUT=$(cd "$GIT" && XDG_CACHE_HOME="$STOP_CACHE" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$POST_HOOK" < "$HOOK_JSON")
[[ -z "$HOOK_OUT" ]] || fail "Post hook should emit no stdout (got: $HOOK_OUT)"

echo "PASS: post-design-boundary deprecation harness"
