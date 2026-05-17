#!/usr/bin/env bash
# Integration tests for skills/implement/scripts/post-design-boundary.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
WRAPPER="$REPO_ROOT/skills/implement/scripts/post-design-boundary.sh"
POST_HOOK="$REPO_ROOT/skills/implement/scripts/hook-post-design.sh"
STOP_HOOK="$REPO_ROOT/skills/implement/scripts/hook-stop-fail-close.sh"
WRITE_SESSION_ENV="$REPO_ROOT/scripts/write-session-env.sh"

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -x "$WRAPPER" ]] || fail "wrapper missing or not executable"
[[ -x "$POST_HOOK" ]] || fail "post-design hook missing or not executable"
[[ -x "$STOP_HOOK" ]] || fail "stop hook missing or not executable"

TMPROOT=$(mktemp -d)
trap 'rm -rf "$TMPROOT"' EXIT
unset LARCH_TOKEN_SESSION_ID
unset LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS

make_manifest() {
    local tmpdir="$1"
    mkdir -p "$tmpdir/design-export"
    printf 'test plan body\n' > "$tmpdir/design-export/plan.txt"
    printf 'tally\n' > "$tmpdir/design-export/voting-tally.md"
    : > "$tmpdir/design-export/contested-decisions.md"
    : > "$tmpdir/design-export/oos.md"
    : > "$tmpdir/design-export/rejected-findings.md"
    : > "$tmpdir/design-export/accepted-plan-findings.md"
    cat > "$tmpdir/design-export/manifest.env" <<EOF_MANIFEST
MANIFEST_VERSION=1
PLAN_FILE=$tmpdir/design-export/plan.txt
PLAN_REVIEW_TALLY_FILE=$tmpdir/design-export/voting-tally.md
CONTESTED_CRITERIA_FILE=$tmpdir/design-export/contested-decisions.md
OOS_FILE=$tmpdir/design-export/oos.md
REJECTED_FINDINGS_FILE=$tmpdir/design-export/rejected-findings.md
ACCEPTED_PLAN_FINDINGS_FILE=$tmpdir/design-export/accepted-plan-findings.md
TIMESTAMP=2026-01-01T00:00:00Z
SESSION_ID=test-session
EOF_MANIFEST
}

make_git_repo() {
    local dir="$1"
    mkdir -p "$dir"
    git -C "$dir" init -q
    git -C "$dir" checkout -q -b boundary-test
}

make_committed_git_repo() {
    local dir="$1"
    make_git_repo "$dir"
    git -C "$dir" config user.email "test@example.invalid"
    git -C "$dir" config user.name "Boundary Test"
    printf 'x\n' > "$dir/file.txt"
    git -C "$dir" add file.txt
    git -C "$dir" commit -q -m init
}

assert_contains() {
    local output="$1"
    local pattern="$2"
    local label="$3"
    if ! printf '%s\n' "$output" | grep -q -- "$pattern"; then
        fail "$label"
    fi
}

assert_not_contains() {
    local output="$1"
    local pattern="$2"
    local label="$3"
    if printf '%s\n' "$output" | grep -q -- "$pattern"; then
        fail "$label"
    fi
}

assert_empty() {
    local output="$1"
    local label="$2"
    [[ -z "$output" ]] || fail "$label"
}

# write-session-env accepts and omits token telemetry flags as expected.
SESSION_WRITER_OUT="$TMPROOT/session-writer.env"
"$WRITE_SESSION_ENV" \
    --output "$SESSION_WRITER_OUT" \
    --repo owner/repo \
    --repo-unavailable false \
    --token-session-id token-session-1 \
    --claude-source-file "$TMPROOT/claude-source.env"
grep -q '^LARCH_TOKEN_SESSION_ID=token-session-1$' "$SESSION_WRITER_OUT" || fail "writer did not emit accepted LARCH_TOKEN_SESSION_ID"
grep -q "^LARCH_CLAUDE_SOURCE_FILE=$TMPROOT/claude-source.env$" "$SESSION_WRITER_OUT" || fail "writer did not emit accepted LARCH_CLAUDE_SOURCE_FILE"
SESSION_WRITER_MIN="$TMPROOT/session-writer-min.env"
"$WRITE_SESSION_ENV" \
    --output "$SESSION_WRITER_MIN" \
    --repo owner/repo \
    --repo-unavailable false
grep -q '^LARCH_TOKEN_SESSION_ID=' "$SESSION_WRITER_MIN" && fail "writer emitted absent LARCH_TOKEN_SESSION_ID"
grep -q '^LARCH_CLAUDE_SOURCE_FILE=' "$SESSION_WRITER_MIN" && fail "writer emitted absent LARCH_CLAUDE_SOURCE_FILE"
if "$WRITE_SESSION_ENV" --output /dev/null --repo owner/repo --repo-unavailable false --token-session-id $'bad\nid' 2>/dev/null; then
    fail "writer accepted newline in --token-session-id"
fi
if "$WRITE_SESSION_ENV" --output /dev/null --repo owner/repo --repo-unavailable false --token-session-id 'bad=id' 2>/dev/null; then
    fail "writer accepted equals in --token-session-id"
fi
if "$WRITE_SESSION_ENV" --output /dev/null --repo owner/repo --repo-unavailable false --claude-source-file $'bad\001path' 2>/dev/null; then
    fail "writer accepted control character in --claude-source-file"
fi

# Success path: reader OK, branch captured, wrapper OK, imperative final line.
TMP1="$TMPROOT/success"
GIT1="$TMPROOT/git-success"
make_manifest "$TMP1"
make_git_repo "$GIT1"
OUT=$(cd "$GIT1" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP1")
assert_contains "$OUT" '^MANIFEST_OK=true$' "success path missing MANIFEST_OK=true"
assert_contains "$OUT" '^BRANCH=boundary-test$' "success path missing BRANCH=boundary-test"
assert_contains "$OUT" '^POST_DESIGN_BOUNDARY_OK=true$' "success path missing POST_DESIGN_BOUNDARY_OK=true"
LAST_LINE=$(printf '%s\n' "$OUT" | tail -n 1)
case "$LAST_LINE" in
    "➡️ 1: design plan — boundary gate passed;"*) ;;
    *) fail "success path final line is not the default imperative breadcrumb: $LAST_LINE" ;;
esac
[[ -f "$TMP1/.boundary-gate-passed" ]] || fail "success path did not write boundary sentinel"
OUT=$(cd "$GIT1" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP1")
assert_contains "$OUT" '^POST_DESIGN_BOUNDARY_OK=true$' "success sentinel path was not idempotent"

# Missing manifest fails closed and suppresses success markers.
TMP2="$TMPROOT/missing"
GIT2="$TMPROOT/git-missing"
mkdir -p "$TMP2"
make_git_repo "$GIT2"
OUT=$(cd "$GIT2" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP2")
assert_contains "$OUT" '^MANIFEST_FAILED=true$' "missing manifest did not fail closed"
assert_not_contains "$OUT" 'POST_DESIGN_BOUNDARY_OK=true' "missing manifest emitted success marker"
assert_not_contains "$OUT" '➡️ 1: design plan' "missing manifest emitted imperative breadcrumb"
[[ ! -f "$TMP2/.boundary-gate-passed" ]] || fail "missing manifest wrote boundary sentinel"

# Boundary sentinel write failure fails closed and suppresses success markers.
TMP2A="$TMPROOT/sentinel-write-fail"
GIT2A="$TMPROOT/git-sentinel-write-fail"
make_manifest "$TMP2A"
make_git_repo "$GIT2A"
chmod 0500 "$TMP2A"
OUT=$(cd "$GIT2A" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP2A")
chmod 0700 "$TMP2A"
assert_contains "$OUT" '^MANIFEST_FAILED=true$' "sentinel write failure did not fail closed"
assert_contains "$OUT" '^ERROR=boundary-gate-sentinel-write-failed$' "sentinel write failure emitted wrong error"
assert_not_contains "$OUT" '^POST_DESIGN_BOUNDARY_OK=true$' "sentinel write failure emitted success marker"

# Invalid tmpdir fails closed.
OUT=$(CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "relative-tmpdir")
assert_contains "$OUT" '^MANIFEST_FAILED=true$' "relative tmpdir did not fail closed"
assert_contains "$OUT" '^ERROR=invalid-tmpdir$' "relative tmpdir did not emit invalid-tmpdir"
assert_not_contains "$OUT" 'POST_DESIGN_BOUNDARY_OK=true' "invalid tmpdir emitted success marker"
assert_not_contains "$OUT" '➡️ 1: design plan' "invalid tmpdir emitted imperative breadcrumb"

# Anchored parse: path text containing MANIFEST_FAILED=true must not affect OK classification.
TMP3="$TMPROOT/MANIFEST_FAILED=true-anchor"
GIT3="$TMPROOT/git-anchor"
make_manifest "$TMP3"
make_git_repo "$GIT3"
OUT=$(cd "$GIT3" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP3")
assert_contains "$OUT" '^MANIFEST_OK=true$' "anchored parse fixture did not remain OK"
assert_contains "$OUT" '^POST_DESIGN_BOUNDARY_OK=true$' "anchored parse fixture missing wrapper success"

# Detached HEAD fails branch capture after retry and emits a clean failure
# envelope (no MANIFEST_OK, no 📥 breadcrumb, no success markers). This is the
# regression guard for the dual-envelope bug where a successful reader read
# was emitted before branch capture, leaving stdout with both MANIFEST_OK=true
# and a trailing MANIFEST_FAILED=true.
TMP8="$TMPROOT/branch-fail"
GIT8="$TMPROOT/git-branch-fail"
make_manifest "$TMP8"
make_committed_git_repo "$GIT8"
git -C "$GIT8" checkout -q --detach HEAD
OUT=$(cd "$GIT8" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP8")
assert_contains "$OUT" '^MANIFEST_FAILED=true$' "detached HEAD did not fail closed"
assert_contains "$OUT" '^ERROR=branch-capture-failed$' "detached HEAD did not emit branch-capture-failed"
assert_not_contains "$OUT" '^MANIFEST_OK=true$' "detached HEAD emitted MANIFEST_OK=true (dual-envelope regression)"
assert_not_contains "$OUT" '📥 1: design plan' "detached HEAD emitted reader breadcrumb (dual-envelope regression)"
assert_not_contains "$OUT" 'POST_DESIGN_BOUNDARY_OK=true' "detached HEAD emitted success marker"
assert_not_contains "$OUT" '➡️ 1: design plan' "detached HEAD emitted imperative breadcrumb"

# Design-only variant emits the design-only imperative.
TMP9="$TMPROOT/design-only"
GIT9="$TMPROOT/git-design-only"
make_manifest "$TMP9"
make_git_repo "$GIT9"
OUT=$(cd "$GIT9" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP9" --design-only true)
LAST_LINE=$(printf '%s\n' "$OUT" | tail -n 1)
case "$LAST_LINE" in
    "➡️ 1: design plan — boundary gate passed (design-only);"*) ;;
    *) fail "design-only path final line is not the design-only imperative breadcrumb: $LAST_LINE" ;;
esac

# --hook-mode: sentinel NOT written, HOOK_INJECTED token emitted, ➡️ still present.
TMP_HM="$TMPROOT/hook-mode"
GIT_HM="$TMPROOT/git-hook-mode"
make_manifest "$TMP_HM"
make_git_repo "$GIT_HM"
OUT=$(cd "$GIT_HM" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP_HM" --hook-mode true)
assert_contains "$OUT" '^MANIFEST_OK=true$' "hook-mode missing MANIFEST_OK=true"
assert_contains "$OUT" '^BRANCH=boundary-test$' "hook-mode missing BRANCH="
assert_contains "$OUT" '^POST_DESIGN_BOUNDARY_HOOK_INJECTED=true$' "hook-mode missing hook-injected token"
assert_not_contains "$OUT" 'POST_DESIGN_BOUNDARY_OK=true' "hook-mode emitted orchestrator success token"
[[ ! -f "$TMP_HM/.boundary-gate-passed" ]] || fail "hook-mode wrote .boundary-gate-passed sentinel"
LAST_HM=$(printf '%s\n' "$OUT" | tail -n 1)
case "$LAST_HM" in
    "➡️ 1: design plan — hook injected boundary context;"*) ;;
    *) fail "hook-mode final line is not hook-injected breadcrumb: $LAST_HM" ;;
esac

# --hook-mode design-only variant.
TMP_HM_DO="$TMPROOT/hook-mode-do"
GIT_HM_DO="$TMPROOT/git-hook-mode-do"
make_manifest "$TMP_HM_DO"
make_git_repo "$GIT_HM_DO"
OUT=$(cd "$GIT_HM_DO" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP_HM_DO" --hook-mode true --design-only true)
assert_contains "$OUT" '^POST_DESIGN_BOUNDARY_HOOK_INJECTED=true$' "hook-mode design-only missing hook-injected token"
assert_not_contains "$OUT" 'POST_DESIGN_BOUNDARY_OK=true' "hook-mode design-only emitted orchestrator success token"
[[ ! -f "$TMP_HM_DO/.boundary-gate-passed" ]] || fail "hook-mode design-only wrote sentinel"
LAST_HM_DO=$(printf '%s\n' "$OUT" | tail -n 1)
case "$LAST_HM_DO" in
    "➡️ 1: design plan — hook injected boundary context (design-only);"*) ;;
    *) fail "hook-mode design-only final line is not hook-injected breadcrumb: $LAST_HM_DO" ;;
esac

# Stop hook still blocks after hook-mode (sentinel absent = hook did not write it).
STOP_CACHE_HM="$TMPROOT/stop-cache-hm"
STOP_CWD_HM="$TMPROOT/stop-cwd-hm"
TMP_SHM="$STOP_CACHE_HM/larch/sessions/claude-implement-hook-stop"
mkdir -p "$STOP_CWD_HM"
make_manifest "$TMP_SHM"
printf 'CLONE_PATH=%s\n' "$STOP_CWD_HM" > "$TMP_SHM/.larch-keepalive"
# Simulate: hook ran (no sentinel), orchestrator halted — Stop hook should block.
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$STOP_CWD_HM" \
    | XDG_CACHE_HOME="$STOP_CACHE_HM" bash "$STOP_HOOK")
assert_contains "$OUT" '"decision":"block"' "Stop hook did not block after hook-mode (sentinel absent)"
# After orchestrator's Bash wrapper runs (non-hook-mode, writes sentinel), Stop allows.
touch "$TMP_SHM/.boundary-gate-passed"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$STOP_CWD_HM" \
    | XDG_CACHE_HOME="$STOP_CACHE_HM" bash "$STOP_HOOK")
assert_empty "$OUT" "Stop hook blocked after orchestrator wrote sentinel"

# PostToolUse hook passes --hook-mode true and injects hook-mode wrapper stdout.
HOOK_CACHE="$TMPROOT/hook-cache"
HOOK_CWD="$TMPROOT/hook-cwd"
TMP12="$HOOK_CACHE/larch/sessions/claude-implement-hook"
GIT12="$TMPROOT/git-hook"
mkdir -p "$HOOK_CWD"
make_manifest "$TMP12"
make_git_repo "$GIT12"
printf 'CLONE_PATH=%s\n' "$HOOK_CWD" > "$TMP12/.larch-keepalive"
printf 'true\n' > "$TMP12/.design-only"
JSON12="$TMPROOT/hook.json"
DECODED12="$TMPROOT/decoded-hook.out"
printf '{"tool_name":"Skill","tool_input":{"skill":"design"},"cwd":"%s"}' "$HOOK_CWD" \
    | (cd "$GIT12" && XDG_CACHE_HOME="$HOOK_CACHE" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$POST_HOOK") > "$JSON12"
jq -j '.hookSpecificOutput.additionalContext' "$JSON12" > "$DECODED12"
# Hook output must be hook-mode (no sentinel written, HOOK_INJECTED token).
assert_contains "$(cat "$DECODED12")" '^POST_DESIGN_BOUNDARY_HOOK_INJECTED=true$' "PostToolUse hook did not pass --hook-mode to wrapper"
assert_not_contains "$(cat "$DECODED12")" 'POST_DESIGN_BOUNDARY_OK=true' "PostToolUse hook emitted orchestrator success token"
[[ ! -f "$TMP12/.boundary-gate-passed" ]] || fail "PostToolUse hook wrote sentinel via --hook-mode"

# PostToolUse no-op paths.
OUT=$(printf '{"tool_name":"Skill","tool_input":{"skill":"review"},"cwd":"%s"}' "$HOOK_CWD" \
    | XDG_CACHE_HOME="$HOOK_CACHE" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$POST_HOOK")
assert_empty "$OUT" "non-design Skill hook path emitted stdout"
OUT=$(printf '{"tool_name":"Skill","tool_input":{"skill":"design"},"cwd":"%s"}' "$TMPROOT/no-such-cwd" \
    | XDG_CACHE_HOME="$HOOK_CACHE" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$POST_HOOK")
assert_empty "$OUT" "hook with no cwd-bound tmpdir emitted stdout"

# Stop hook blocks only while manifest exists and neither release sentinel exists.
STOP_CACHE="$TMPROOT/stop-cache"
STOP_CWD="$TMPROOT/stop-cwd"
TMP13="$STOP_CACHE/larch/sessions/claude-implement-stop"
mkdir -p "$STOP_CWD"
make_manifest "$TMP13"
printf 'CLONE_PATH=%s\n' "$STOP_CWD" > "$TMP13/.larch-keepalive"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$STOP_CWD" \
    | XDG_CACHE_HOME="$STOP_CACHE" bash "$STOP_HOOK")
assert_contains "$OUT" '"decision":"block"' "Stop hook did not emit block decision"
assert_contains "$OUT" "post-/design boundary" "Stop hook reason missing boundary text"
assert_contains "$OUT" "$(basename "$TMP13")" "Stop hook reason missing tmpdir basename"
assert_not_contains "$OUT" "$TMP13" "Stop hook leaked full tmpdir path"

touch "$TMP13/.boundary-gate-passed"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$STOP_CWD" \
    | XDG_CACHE_HOME="$STOP_CACHE" bash "$STOP_HOOK")
assert_empty "$OUT" "Stop hook blocked after boundary sentinel"
rm -f "$TMP13/.boundary-gate-passed"
touch "$TMP13/.run-cleaned-up"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$STOP_CWD" \
    | XDG_CACHE_HOME="$STOP_CACHE" bash "$STOP_HOOK")
assert_empty "$OUT" "Stop hook blocked after cleanup sentinel"
rm -f "$TMP13/.run-cleaned-up" "$TMP13/design-export/manifest.env"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$STOP_CWD" \
    | XDG_CACHE_HOME="$STOP_CACHE" bash "$STOP_HOOK")
assert_empty "$OUT" "Stop hook blocked without manifest"
make_manifest "$TMP13"
OUT=$(printf '{"cwd":"%s","stop_hook_active":true}' "$STOP_CWD" \
    | XDG_CACHE_HOME="$STOP_CACHE" bash "$STOP_HOOK")
assert_empty "$OUT" "Stop hook blocked continuation-loop reentry"

# Concurrent-session disambiguation: cwd selects the matching keepalive only.
STOP_CWD_A="$TMPROOT/stop-cwd-a"
STOP_CWD_B="$TMPROOT/stop-cwd-b"
TMP14A="$STOP_CACHE/larch/sessions/claude-implement-a"
TMP14B="$STOP_CACHE/larch/sessions/claude-implement-b"
mkdir -p "$STOP_CWD_A" "$STOP_CWD_B"
make_manifest "$TMP14A"
make_manifest "$TMP14B"
printf 'CLONE_PATH=%s\n' "$STOP_CWD_A" > "$TMP14A/.larch-keepalive"
printf 'CLONE_PATH=%s\n' "$STOP_CWD_B" > "$TMP14B/.larch-keepalive"
touch "$TMP14A/design-export/manifest.env" "$TMP14B/design-export/manifest.env"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$STOP_CWD_A" \
    | XDG_CACHE_HOME="$STOP_CACHE" bash "$STOP_HOOK")
assert_contains "$OUT" "$(basename "$TMP14A")" "Stop hook did not resolve cwd A"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$STOP_CWD_B" \
    | XDG_CACHE_HOME="$STOP_CACHE" bash "$STOP_HOOK")
assert_contains "$OUT" "$(basename "$TMP14B")" "Stop hook did not resolve cwd B"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$TMPROOT/stop-cwd-none" \
    | XDG_CACHE_HOME="$STOP_CACHE" bash "$STOP_HOOK")
assert_empty "$OUT" "Stop hook did not fail open with no cwd match"

# Fail-open when cwd is missing or empty in stdin: PostToolUse and Stop hooks
# must NOT pick the globally-newest manifest under accumulated session state.
OUT=$(printf '{"tool_name":"Skill","tool_input":{"skill":"design"}}' \
    | XDG_CACHE_HOME="$STOP_CACHE" bash "$POST_HOOK")
assert_empty "$OUT" "PostToolUse hook did not fail open with missing cwd"

OUT=$(printf '{"tool_name":"Skill","tool_input":{"skill":"design"},"cwd":""}' \
    | XDG_CACHE_HOME="$STOP_CACHE" bash "$POST_HOOK")
assert_empty "$OUT" "PostToolUse hook did not fail open with empty cwd"

OUT=$(printf '{"stop_hook_active":false}' \
    | XDG_CACHE_HOME="$STOP_CACHE" bash "$STOP_HOOK")
assert_empty "$OUT" "Stop hook did not fail open with missing cwd"

OUT=$(printf '{"cwd":"","stop_hook_active":false}' \
    | XDG_CACHE_HOME="$STOP_CACHE" bash "$STOP_HOOK")
assert_empty "$OUT" "Stop hook did not fail open with empty cwd"

# Path-injection defense rejects control characters.
CONTROL_PATH="$TMPROOT/"$'bad\npath'
OUT=$(CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$CONTROL_PATH")
assert_contains "$OUT" '^MANIFEST_FAILED=true$' "control-char tmpdir did not fail closed"
assert_contains "$OUT" '^ERROR=invalid-tmpdir$' "control-char tmpdir did not emit invalid-tmpdir"
assert_not_contains "$OUT" 'POST_DESIGN_BOUNDARY_OK=true' "control-char tmpdir emitted success marker"

# --session-env validation: relative path is rejected with invalid-session-env.
TMP10="$TMPROOT/session-rel"
GIT10="$TMPROOT/git-session-rel"
make_manifest "$TMP10"
make_git_repo "$GIT10"
OUT=$(cd "$GIT10" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP10" --session-env "relative/session-env.sh")
assert_contains "$OUT" '^MANIFEST_FAILED=true$' "relative session-env did not fail closed"
assert_contains "$OUT" '^ERROR=invalid-session-env$' "relative session-env did not emit invalid-session-env"
assert_not_contains "$OUT" 'POST_DESIGN_BOUNDARY_OK=true' "relative session-env emitted success marker"

# --session-env validation: control-character path is rejected with invalid-session-env.
TMP11="$TMPROOT/session-ctrl"
GIT11="$TMPROOT/git-session-ctrl"
make_manifest "$TMP11"
make_git_repo "$GIT11"
CONTROL_SESSION="$TMPROOT/"$'bad\nsession.sh'
OUT=$(cd "$GIT11" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP11" --session-env "$CONTROL_SESSION")
assert_contains "$OUT" '^MANIFEST_FAILED=true$' "control-char session-env did not fail closed"
assert_contains "$OUT" '^ERROR=invalid-session-env$' "control-char session-env did not emit invalid-session-env"
assert_not_contains "$OUT" 'POST_DESIGN_BOUNDARY_OK=true' "control-char session-env emitted success marker"

# TTL / session-id binding for hook tmpdir resolution.
TTL_CACHE="$TMPROOT/ttl-cache"
TTL_CWD="$TMPROOT/ttl-cwd"
mkdir -p "$TTL_CWD"

TMP15="$TTL_CACHE/larch/sessions/claude-implement-stale"
make_manifest "$TMP15"
printf 'CLONE_PATH=%s\n' "$TTL_CWD" > "$TMP15/.larch-keepalive"
touch -t 200001010000 "$TMP15/design-export/manifest.env"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$TTL_CWD" \
    | XDG_CACHE_HOME="$TTL_CACHE" LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS=1 bash "$STOP_HOOK")
assert_empty "$OUT" "stale tmpdir without session id did not fail open"

TMP16="$TTL_CACHE/larch/sessions/claude-implement-fresh"
make_manifest "$TMP16"
printf 'CLONE_PATH=%s\n' "$TTL_CWD" > "$TMP16/.larch-keepalive"
touch "$TMP16/design-export/manifest.env"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$TTL_CWD" \
    | XDG_CACHE_HOME="$TTL_CACHE" LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS=21600 bash "$STOP_HOOK")
assert_contains "$OUT" '"decision":"block"' "fresh tmpdir without session id did not block"
touch "$TMP16/.run-cleaned-up"

TMP17="$TTL_CACHE/larch/sessions/claude-implement-session-mismatch"
make_manifest "$TMP17"
printf 'CLONE_PATH=%s\nSESSION_ID=session-A\n' "$TTL_CWD" > "$TMP17/.larch-keepalive"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$TTL_CWD" \
    | XDG_CACHE_HOME="$TTL_CACHE" LARCH_TOKEN_SESSION_ID=session-B bash "$STOP_HOOK")
assert_empty "$OUT" "session-id mismatch did not disqualify candidate"
rm -f "$TMP17/design-export/manifest.env"

TMP18="$TTL_CACHE/larch/sessions/claude-implement-session-match"
make_manifest "$TMP18"
printf 'CLONE_PATH=%s\nSESSION_ID=session-A\n' "$TTL_CWD" > "$TMP18/.larch-keepalive"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$TTL_CWD" \
    | XDG_CACHE_HOME="$TTL_CACHE" LARCH_TOKEN_SESSION_ID=session-A bash "$STOP_HOOK")
assert_contains "$OUT" '"decision":"block"' "session-id match did not block"
touch "$TMP18/.run-cleaned-up"
rm -f "$TMP18/design-export/manifest.env"

TMP19="$TTL_CACHE/larch/sessions/claude-implement-session-match-stale"
make_manifest "$TMP19"
printf 'CLONE_PATH=%s\nSESSION_ID=session-A\n' "$TTL_CWD" > "$TMP19/.larch-keepalive"
touch -t 200001010000 "$TMP19/design-export/manifest.env"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$TTL_CWD" \
    | XDG_CACHE_HOME="$TTL_CACHE" LARCH_TOKEN_SESSION_ID=session-A LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS=1 bash "$STOP_HOOK")
assert_contains "$OUT" '"decision":"block"' "session-id match did not bypass TTL"
touch "$TMP19/.run-cleaned-up"
rm -f "$TMP19/design-export/manifest.env"

TMP20="$TTL_CACHE/larch/sessions/claude-implement-session-missing"
make_manifest "$TMP20"
printf 'CLONE_PATH=%s\n' "$TTL_CWD" > "$TMP20/.larch-keepalive"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$TTL_CWD" \
    | XDG_CACHE_HOME="$TTL_CACHE" LARCH_TOKEN_SESSION_ID=session-A bash "$STOP_HOOK")
assert_empty "$OUT" "env-set keepalive without SESSION_ID did not disqualify candidate"

TMP21="$TTL_CACHE/larch/sessions/claude-implement-date-broken"
make_manifest "$TMP21"
printf 'CLONE_PATH=%s\n' "$TTL_CWD" > "$TMP21/.larch-keepalive"
touch "$TMP21/design-export/manifest.env"
DATELESS_BIN="$TMPROOT/dateless-bin"
mkdir -p "$DATELESS_BIN"
for tool in awk stat; do
    tool_path=$(command -v "$tool" || true)
    [[ -n "$tool_path" ]] && ln -s "$tool_path" "$DATELESS_BIN/$tool"
done
BASH_BIN=$(command -v bash || true)
[[ -n "$BASH_BIN" ]] || fail "could not resolve bash for dateless resolver fixture"
# shellcheck disable=SC2016
OUT=$(PATH="$DATELESS_BIN" XDG_CACHE_HOME="$TTL_CACHE" LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS=21600 \
    "$BASH_BIN" -c 'source "$1"; resolve_implement_tmpdir "$2"' _ "$REPO_ROOT/skills/implement/scripts/lib-resolve-implement-tmpdir.sh" "$TTL_CWD")
assert_empty "$OUT" "date +%s failure did not reject TTL-only candidate"

# Boundary: a candidate exactly TTL seconds old is treated as stale (>=).
# Set mtime precisely to (now - TTL) so age == ttl at evaluation; under the
# prior strict-`>` rule this would have been treated as fresh. Uses an
# isolated cache root so unrelated prior fixtures cannot satisfy resolution.
BOUNDARY_CACHE="$TMPROOT/ttl-boundary-cache"
BOUNDARY_CWD="$TMPROOT/ttl-boundary-cwd"
mkdir -p "$BOUNDARY_CWD"
TMP22="$BOUNDARY_CACHE/larch/sessions/claude-implement-ttl-boundary"
make_manifest "$TMP22"
printf 'CLONE_PATH=%s\n' "$BOUNDARY_CWD" > "$TMP22/.larch-keepalive"
BOUNDARY_TTL=10
BOUNDARY_TS=$(($(date +%s) - BOUNDARY_TTL))
# Cross-platform mtime set: try GNU date, then BSD date.
if BOUNDARY_FMT=$(date -d "@$BOUNDARY_TS" +%Y%m%d%H%M.%S 2>/dev/null); then
    touch -t "$BOUNDARY_FMT" "$TMP22/design-export/manifest.env"
elif BOUNDARY_FMT=$(date -r "$BOUNDARY_TS" +%Y%m%d%H%M.%S 2>/dev/null); then
    touch -t "$BOUNDARY_FMT" "$TMP22/design-export/manifest.env"
else
    fail "could not compute boundary mtime for TTL boundary fixture"
fi
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$BOUNDARY_CWD" \
    | XDG_CACHE_HOME="$BOUNDARY_CACHE" LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS="$BOUNDARY_TTL" bash "$STOP_HOOK")
assert_empty "$OUT" "candidate at exact TTL boundary did not expire (>= rule)"
rm -f "$TMP22/design-export/manifest.env"

# F4: hook stdin .session_id is surfaced into LARCH_TOKEN_SESSION_ID so
# session-id binding works in production where /implement Step 0's
# in-bash export does not propagate to hook subprocesses. Uses an
# isolated cache root so unrelated prior fixtures cannot win resolution
# under cwd/SESSION_ID combinations. With LARCH_TOKEN_SESSION_ID unset
# in env, the only path that can see the stdin mismatch is the hook's
# explicit `jq -r .session_id` + `export LARCH_TOKEN_SESSION_ID` step.
F4_CACHE="$TMPROOT/f4-stdin-cache"
F4_CWD="$TMPROOT/f4-stdin-cwd"
mkdir -p "$F4_CWD"
TMP23="$F4_CACHE/larch/sessions/claude-implement-stdin-sid-mismatch"
make_manifest "$TMP23"
printf 'CLONE_PATH=%s\nSESSION_ID=session-X\n' "$F4_CWD" > "$TMP23/.larch-keepalive"
touch "$TMP23/design-export/manifest.env"
unset LARCH_TOKEN_SESSION_ID
OUT=$(printf '{"cwd":"%s","stop_hook_active":false,"session_id":"session-Y"}' "$F4_CWD" \
    | XDG_CACHE_HOME="$F4_CACHE" bash "$STOP_HOOK")
assert_empty "$OUT" "stdin session_id was not surfaced into resolver (mismatch should disqualify)"
rm -f "$TMP23/design-export/manifest.env"

# F4: hook stdin .session_id matching keepalive SESSION_ID blocks (positive).
TMP24="$F4_CACHE/larch/sessions/claude-implement-stdin-sid-match"
make_manifest "$TMP24"
printf 'CLONE_PATH=%s\nSESSION_ID=session-Z\n' "$F4_CWD" > "$TMP24/.larch-keepalive"
touch "$TMP24/design-export/manifest.env"
unset LARCH_TOKEN_SESSION_ID
OUT=$(printf '{"cwd":"%s","stop_hook_active":false,"session_id":"session-Z"}' "$F4_CWD" \
    | XDG_CACHE_HOME="$F4_CACHE" bash "$STOP_HOOK")
assert_contains "$OUT" '"decision":"block"' "stdin session_id match did not block"
touch "$TMP24/.run-cleaned-up"
rm -f "$TMP24/design-export/manifest.env"

# Review-boundary Stop hook tests (issue #1862): review-round-summary.md serves
# as the "review ran" sentinel; .review-boundary-passed clears the guard.
# Uses a tmpdir without design-export/manifest.env to cover the both-externals-down
# path (resolver now accepts review-round-summary.md as an alternative sentinel).
REVIEW_CACHE="$TMPROOT/review-boundary-cache"
REVIEW_CWD="$TMPROOT/review-boundary-cwd"
TMP_REV="$REVIEW_CACHE/larch/sessions/claude-implement-review-boundary"
mkdir -p "$REVIEW_CWD" "$TMP_REV"
printf 'review summary content\n' > "$TMP_REV/review-round-summary.md"
printf 'CLONE_PATH=%s\n' "$REVIEW_CWD" > "$TMP_REV/.larch-keepalive"

# Blocks: review ran, boundary not yet cleared (no manifest needed).
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$REVIEW_CWD" \
    | XDG_CACHE_HOME="$REVIEW_CACHE" bash "$STOP_HOOK")
assert_contains "$OUT" '"decision":"block"' "Stop hook did not block post-/review boundary"
assert_contains "$OUT" "post-/review boundary" "Stop hook reason missing review-boundary text"
assert_contains "$OUT" "$(basename "$TMP_REV")" "Stop hook reason missing tmpdir basename for review"
assert_not_contains "$OUT" "$TMP_REV" "Stop hook leaked full review tmpdir path"

# Allows after .review-boundary-passed sentinel is written.
touch "$TMP_REV/.review-boundary-passed"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$REVIEW_CWD" \
    | XDG_CACHE_HOME="$REVIEW_CACHE" bash "$STOP_HOOK")
assert_empty "$OUT" "Stop hook blocked after .review-boundary-passed"

# Allows after .run-cleaned-up (teardown path).
rm -f "$TMP_REV/.review-boundary-passed"
touch "$TMP_REV/.run-cleaned-up"
OUT=$(printf '{"cwd":"%s","stop_hook_active":false}' "$REVIEW_CWD" \
    | XDG_CACHE_HOME="$REVIEW_CACHE" bash "$STOP_HOOK")
assert_empty "$OUT" "Stop hook blocked after .run-cleaned-up (review-boundary path)"

echo "PASS: post-design-boundary wrapper integration tests"
