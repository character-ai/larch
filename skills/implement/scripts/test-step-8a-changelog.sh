#!/usr/bin/env bash
# test-step-8a-changelog.sh — Offline regression harness for the Step 8a
# changelog fallback logic added in Item J of ship-pr-helper-polish-batch-2.
#
# Exercises three fixtures:
#   (a) Valid manifest with summary_bullets_categorized → CHANGELOG_STATUS=updated
#   (b) Empty manifest + ISSUE_NUMBER set → fallback bullet in CHANGELOG.md
#   (c) Empty manifest + ISSUE_NUMBER unset → CHANGELOG_STATUS=fail-no-manifest-no-issue
set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_FINALIZE="$(cd "$SCRIPT_DIR/../../.." && pwd)/scripts/implement-finalize.sh"
REAL_SCRIPTS_DIR="$(dirname "$REAL_FINALIZE")"

[ -x "$REAL_FINALIZE" ] || { echo "FAIL: $REAL_FINALIZE not executable"; exit 1; }

PASS=0
FAIL=0
SANDBOX=""

cleanup() { [ -n "$SANDBOX" ] && [ -d "$SANDBOX" ] && rm -rf "$SANDBOX"; }
trap cleanup EXIT

assert_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -qF -- "$needle"; then
        PASS=$((PASS + 1)); echo "PASS: $label"
    else
        FAIL=$((FAIL + 1)); echo "FAIL: $label"
        echo "  expected to contain: $needle"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    fi
}

assert_file_contains() {
    local needle=$1 path=$2 label=$3
    assert_contains "$needle" "$(cat "$path" 2>/dev/null || true)" "$label"
}

build_sandbox() {
    SANDBOX=$(mktemp -d "${TMPDIR:-/tmp}/larch-test-8a-changelog.XXXXXX")
    local s="$SANDBOX/scripts" r="$SANDBOX/repo" t="$SANDBOX/tmp"
    mkdir -p "$s" "$r" "$t/larch-log-batches" "$t/larch-logs/implement/run-001"

    # --- Real git repo on feature branch with a bump commit ---
    git -C "$r" init -q
    git -C "$r" config user.email "test@test.com"
    git -C "$r" config user.name "Test"
    git -C "$r" checkout -b feature-test >/dev/null 2>&1
    cat > "$r/CHANGELOG.md" <<'CL'
# Changelog

## [Unreleased]

## [1.0.0] - 2025-01-01
### Changed
- Initial release.
CL
    mkdir -p "$r/.claude-plugin"
    printf '{"version":"1.0.0"}\n' > "$r/.claude-plugin/plugin.json"
    git -C "$r" add -A
    git -C "$r" commit -q -m "Initial commit"
    printf '{"version":"1.0.1"}\n' > "$r/.claude-plugin/plugin.json"
    git -C "$r" add .claude-plugin/plugin.json
    git -C "$r" commit -q -m "Bump version to 1.0.1"

    # --- Copy scripts that implement-finalize sources/uses ---
    cp "$REAL_FINALIZE" "$s/implement-finalize.sh"
    cp "$REAL_SCRIPTS_DIR/lib-quiet.sh" "$s/lib-quiet.sh"
    cp "$REAL_SCRIPTS_DIR/lib-execution-issues.sh" "$s/lib-execution-issues.sh"
    chmod +x "$s/implement-finalize.sh"

    # --- Stub scripts (check-changelog-present.sh always reports present) ---
    printf '#!/usr/bin/env bash\nprintf '"'"'CHANGELOG_PRESENT=true\n'"'"'\n' > "$s/check-changelog-present.sh"
    chmod +x "$s/check-changelog-present.sh"

    # larch-log.sh: succeed silently
    cat > "$s/larch-log.sh" <<'SH'
#!/usr/bin/env bash
printf 'LOG_WRITTEN=true\nUNCHANGED=false\nCOMMIT_SHA=abc\n'
SH
    chmod +x "$s/larch-log.sh"

    # git-amend-add.sh: succeed (means amend was applied)
    cat > "$s/git-amend-add.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
# Verify the file was staged; amend.
git add -A 2>/dev/null || true
git commit --amend --no-edit -q 2>/dev/null || true
SH
    chmod +x "$s/git-amend-add.sh"

    # rebase-push.sh: already fresh
    printf '#!/usr/bin/env bash\nprintf '"'"'SKIPPED_ALREADY_FRESH=true\n'"'"'\n' > "$s/rebase-push.sh"
    chmod +x "$s/rebase-push.sh"

    # check-remote-branch.sh: branch absent (no push needed)
    printf '#!/usr/bin/env bash\nprintf '"'"'STATE=absent\n'"'"'\n' > "$s/check-remote-branch.sh"
    chmod +x "$s/check-remote-branch.sh"

    # No-op telemetry stubs
    for stub in read-session-env-key.sh token-ledger.sh timing-ledger.sh \
                token-report.sh timing-report.sh; do
        printf '#!/usr/bin/env bash\nexit 0\n' > "$s/$stub"
        chmod +x "$s/$stub"
    done

    # Stub tracking-issue-write.sh and round-trip-detect.sh used in postbump_tail
    cat > "$s/tracking-issue-write.sh" <<'SH'
#!/usr/bin/env bash
printf 'RENAMED=false\nNEW_TITLE=stub\n'
SH
    chmod +x "$s/tracking-issue-write.sh"
    printf '#!/usr/bin/env bash\nprintf '"'"'ROUND_TRIP=false\n'"'"'\n' > "$s/round-trip-detect.sh"
    chmod +x "$s/round-trip-detect.sh"

    # execution-issues log
    touch "$t/execution-issues.md"
}

make_state_file() {
    local issue_num=$1 pr_title=$2 manifest_path=$3 run_id=${4:-run-001}
    local sf="$SANDBOX/tmp/state.sh"
    cat > "$sf" <<STATE
BRANCH_NAME=feature-test
ISSUE_NUMBER=$issue_num
PR_TITLE=$pr_title
REPO=test/repo
REPO_UNAVAILABLE=false
FORKED_TARGET=false
HAS_BUMP=true
BUMP_TYPE=PATCH
NEW_VERSION=1.0.1
BUMP_REASONING_FILE=
MANIFEST_PATH=$manifest_path
TOOL_LABEL=test
RUN_ID=$run_id
STATE
    printf '%s\n' "$sf"
}

run_postbump() {
    local state_file=$1 out
    set +e
    out=$(cd "$SANDBOX/repo" && \
        IMPLEMENT_TMPDIR="$SANDBOX/tmp" \
        LARCH_QUIET_DISABLE=1 \
        LARCH_NO_LOGS_COMMIT=true \
        bash "$SANDBOX/scripts/implement-finalize.sh" postbump \
            --state-file "$state_file" \
            --implement-tmpdir "$SANDBOX/tmp" \
        2>&1)
    set -e
    printf '%s\n' "$out"
}

# ===========================================================================
# Setup common sandbox (shared across fixtures to save time)
# ===========================================================================
build_sandbox

# Create a valid manifest for fixture (a)
MANIFEST_A="$SANDBOX/tmp/manifest-a.json"
cat > "$MANIFEST_A" <<'JSON'
{
  "summary_bullets_categorized": {
    "Changed": ["Fix apply-bump rebase detection", "Add git-push stderr dedup"]
  },
  "commit_message": "test commit"
}
JSON

# ===========================================================================
# Fixture (a): valid manifest → CHANGELOG_STATUS=updated
# ===========================================================================
echo
echo "Fixture (a): valid manifest → CHANGELOG_STATUS=updated"

# Restore clean CHANGELOG.md for each fixture
git -C "$SANDBOX/repo" checkout -- CHANGELOG.md 2>/dev/null || true

state_a=$(make_state_file "42" "Test PR" "$MANIFEST_A")
out_a=$(run_postbump "$state_a")
assert_contains "CHANGELOG_STATUS=updated" "$out_a" "a: CHANGELOG_STATUS=updated"
# CHANGELOG.md should contain the bullet
assert_file_contains "Fix apply-bump rebase detection" "$SANDBOX/repo/CHANGELOG.md" \
    "a: bullet from manifest in CHANGELOG.md"

# ===========================================================================
# Fixture (b): empty manifest + ISSUE_NUMBER set → fallback bullet
# ===========================================================================
echo
echo "Fixture (b): empty manifest + ISSUE_NUMBER → fallback bullet"

git -C "$SANDBOX/repo" checkout -- CHANGELOG.md 2>/dev/null || true

state_b=$(make_state_file "2354" "ship-pr.sh helper polish batch 2" "")
out_b=$(run_postbump "$state_b")
assert_contains "CHANGELOG_STATUS=updated" "$out_b" "b: CHANGELOG_STATUS=updated (fallback)"
assert_file_contains "Closed: #2354" "$SANDBOX/repo/CHANGELOG.md" \
    "b: fallback bullet Closed: #N in CHANGELOG.md"
assert_file_contains "ship-pr.sh helper polish batch 2" "$SANDBOX/repo/CHANGELOG.md" \
    "b: PR title included in fallback bullet"

# ===========================================================================
# Fixture (c): empty manifest + no ISSUE_NUMBER → loud failure
# ===========================================================================
echo
echo "Fixture (c): empty manifest + no ISSUE_NUMBER → fail-no-manifest-no-issue"

git -C "$SANDBOX/repo" checkout -- CHANGELOG.md 2>/dev/null || true

state_c=$(make_state_file "" "" "")
out_c=$(run_postbump "$state_c")
assert_contains "STATUS=changelog-failed" "$out_c" \
    "c: STATUS=changelog-failed"
assert_contains "CHANGELOG_STATUS=fail-no-manifest-no-issue" "$out_c" \
    "c: CHANGELOG_STATUS=fail-no-manifest-no-issue"
# The warn_line writes to stderr, captured by run_postbump's 2>&1 redirect.
assert_contains "summary bullets absent and no tracking-issue context" "$out_c" \
    "c: loud error message present"
assert_file_contains \
    "ERROR=Cannot generate changelog bullet: no manifest AND no tracking-issue context." \
    "$SANDBOX/tmp/execution-issues.md" \
    "c: execution-issues logs stable ERROR line"

# ===========================================================================
echo
TOTAL=$((PASS + FAIL))
echo "test-step-8a-changelog: $PASS/$TOTAL passed"
if [ "$FAIL" -gt 0 ]; then
    echo "FAILED: $FAIL test(s)" >&2
    exit 1
fi
