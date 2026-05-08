#!/usr/bin/env bash
# Integration tests for skills/implement/scripts/post-design-boundary.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
WRAPPER="$REPO_ROOT/skills/implement/scripts/post-design-boundary.sh"
POST_HOOK="$REPO_ROOT/skills/implement/scripts/hook-post-design.sh"
STOP_HOOK="$REPO_ROOT/skills/implement/scripts/hook-stop-fail-close.sh"
READER="$REPO_ROOT/skills/design/scripts/read-design-manifest.sh"
BRANCH_HELPER="$REPO_ROOT/scripts/git-current-branch.sh"

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -x "$WRAPPER" ]] || fail "wrapper missing or not executable"
[[ -x "$POST_HOOK" ]] || fail "post-design hook missing or not executable"
[[ -x "$STOP_HOOK" ]] || fail "stop hook missing or not executable"

TMPROOT=$(mktemp -d)
trap 'rm -rf "$TMPROOT"' EXIT

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

# Health degradation rewrites session-env while preserving non-health values.
TMP4="$TMPROOT/health-flip"
GIT4="$TMPROOT/git-health-flip"
make_manifest "$TMP4"
make_git_repo "$GIT4"
SESSION4="$TMP4/session-env.sh"
cat > "$SESSION4" <<'EOF_SESSION'
SLACK_OK=false
SLACK_MISSING=token,channel
REPO=owner/repo
REPO_UNAVAILABLE=false
CODEX_HEALTHY=true
CURSOR_HEALTHY=true
GEMINI_HEALTHY=true
LARCH_TIMING_LEDGER=/tmp/larch-post-design-boundary-test/timing-ledger.tsv
EOF_SESSION
cat > "$SESSION4.health" <<'EOF_HEALTH'
CODEX_HEALTHY=false
CURSOR_HEALTHY=true
GEMINI_HEALTHY=true
EOF_HEALTH
OUT=$(cd "$GIT4" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP4" --session-env "$SESSION4")
assert_contains "$OUT" '^POST_DESIGN_BOUNDARY_OK=true$' "health flip path did not continue"
grep -q '^SLACK_OK=false$' "$SESSION4" || fail "health rewrite did not preserve SLACK_OK"
grep -q '^SLACK_MISSING=token,channel$' "$SESSION4" || fail "health rewrite did not preserve SLACK_MISSING"
grep -q '^REPO=owner/repo$' "$SESSION4" || fail "health rewrite did not preserve REPO"
grep -q '^REPO_UNAVAILABLE=false$' "$SESSION4" || fail "health rewrite did not preserve REPO_UNAVAILABLE"
grep -q '^CODEX_HEALTHY=false$' "$SESSION4" || fail "health rewrite did not degrade CODEX_HEALTHY"
grep -q '^CURSOR_HEALTHY=true$' "$SESSION4" || fail "health rewrite did not preserve CURSOR_HEALTHY"
grep -q '^GEMINI_HEALTHY=true$' "$SESSION4" || fail "health rewrite did not preserve GEMINI_HEALTHY"
grep -q '^LARCH_TIMING_LEDGER=/tmp/larch-post-design-boundary-test/timing-ledger.tsv$' "$SESSION4" || fail "health rewrite did not preserve LARCH_TIMING_LEDGER"

# Missing sidecar is a no-op and emits no warning.
TMP5="$TMPROOT/health-absent"
GIT5="$TMPROOT/git-health-absent"
make_manifest "$TMP5"
make_git_repo "$GIT5"
SESSION5="$TMP5/session-env.sh"
cp "$SESSION4" "$SESSION5"
BEFORE5=$(cat "$SESSION5")
OUT=$(cd "$GIT5" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP5" --session-env "$SESSION5")
AFTER5=$(cat "$SESSION5")
[[ "$BEFORE5" = "$AFTER5" ]] || fail "missing sidecar rewrote session-env"
assert_not_contains "$OUT" '^WARN=' "missing sidecar emitted warning"

# Malformed boolean preserves prior value and warns.
TMP6="$TMPROOT/health-malformed"
GIT6="$TMPROOT/git-health-malformed"
make_manifest "$TMP6"
make_git_repo "$GIT6"
SESSION6="$TMP6/session-env.sh"
cat > "$SESSION6" <<'EOF_SESSION'
SLACK_OK=true
SLACK_MISSING=
REPO=owner/repo
REPO_UNAVAILABLE=false
CODEX_HEALTHY=true
CURSOR_HEALTHY=true
GEMINI_HEALTHY=true
EOF_SESSION
cat > "$SESSION6.health" <<'EOF_HEALTH'
CODEX_HEALTHY=maybe
CURSOR_HEALTHY=true
GEMINI_HEALTHY=true
EOF_HEALTH
BEFORE6=$(cat "$SESSION6")
OUT=$(cd "$GIT6" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP6" --session-env "$SESSION6")
AFTER6=$(cat "$SESSION6")
[[ "$BEFORE6" = "$AFTER6" ]] || fail "malformed health value rewrote session-env"
assert_contains "$OUT" '^WARN=health-value-invalid:CODEX_HEALTHY$' "malformed health value did not warn"
assert_contains "$OUT" '^POST_DESIGN_BOUNDARY_OK=true$' "malformed health value did not continue"

# write-session-env failure is non-fatal.
TMP7="$TMPROOT/health-write-fail"
GIT7="$TMPROOT/git-health-write-fail"
FAKE_ROOT="$TMPROOT/fake-plugin-root"
make_manifest "$TMP7"
make_git_repo "$GIT7"
mkdir -p "$FAKE_ROOT/skills/design/scripts" "$FAKE_ROOT/scripts"
ln -s "$READER" "$FAKE_ROOT/skills/design/scripts/read-design-manifest.sh"
ln -s "$BRANCH_HELPER" "$FAKE_ROOT/scripts/git-current-branch.sh"
cat > "$FAKE_ROOT/scripts/write-session-env.sh" <<'EOF_FAIL'
#!/usr/bin/env bash
exit 1
EOF_FAIL
chmod +x "$FAKE_ROOT/scripts/write-session-env.sh"
SESSION7="$TMP7/session-env.sh"
cat > "$SESSION7" <<'EOF_SESSION'
SLACK_OK=true
SLACK_MISSING=
REPO=owner/repo
REPO_UNAVAILABLE=false
CODEX_HEALTHY=true
CURSOR_HEALTHY=true
GEMINI_HEALTHY=true
EOF_SESSION
cat > "$SESSION7.health" <<'EOF_HEALTH'
CODEX_HEALTHY=true
CURSOR_HEALTHY=false
GEMINI_HEALTHY=true
EOF_HEALTH
OUT=$(cd "$GIT7" && CLAUDE_PLUGIN_ROOT="$FAKE_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP7" --session-env "$SESSION7")
assert_contains "$OUT" '^WARN=health-merge-failed$' "write-session-env failure did not warn"
assert_contains "$OUT" '^POST_DESIGN_BOUNDARY_OK=true$' "write-session-env failure did not continue"
LAST_LINE=$(printf '%s\n' "$OUT" | tail -n 1)
case "$LAST_LINE" in
    "➡️ 1: design plan — boundary gate passed;"*) ;;
    *) fail "write failure path final line is not the imperative breadcrumb: $LAST_LINE" ;;
esac

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

# PostToolUse hook injects byte-identical wrapper stdout, including trailing newline.
HOOK_CACHE="$TMPROOT/hook-cache"
HOOK_CWD="$TMPROOT/hook-cwd"
TMP12="$HOOK_CACHE/larch/sessions/claude-implement-hook"
GIT12="$TMPROOT/git-hook"
mkdir -p "$HOOK_CWD"
make_manifest "$TMP12"
make_git_repo "$GIT12"
printf 'CLONE_PATH=%s\n' "$HOOK_CWD" > "$TMP12/.larch-keepalive"
printf 'true\n' > "$TMP12/.design-only"
DIRECT12="$TMPROOT/direct-hook.out"
DECODED12="$TMPROOT/decoded-hook.out"
JSON12="$TMPROOT/hook.json"
(cd "$GIT12" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$WRAPPER" --implement-tmpdir "$TMP12" --session-env "$TMP12/session-env.sh" --design-only true > "$DIRECT12")
printf '{"tool_name":"Skill","tool_input":{"skill":"design"},"cwd":"%s"}' "$HOOK_CWD" \
    | (cd "$GIT12" && XDG_CACHE_HOME="$HOOK_CACHE" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$POST_HOOK") > "$JSON12"
jq -j '.hookSpecificOutput.additionalContext' "$JSON12" > "$DECODED12"
cmp "$DIRECT12" "$DECODED12" >/dev/null || fail "PostToolUse additionalContext was not byte-identical to wrapper stdout"

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

echo "PASS: post-design-boundary wrapper integration tests"
