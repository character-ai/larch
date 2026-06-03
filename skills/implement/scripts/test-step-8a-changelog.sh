#!/usr/bin/env bash
# test-step-8a-changelog.sh — Phase 1 (#3364) regression: implement-finalize postbump
# must not write CHANGELOG.md or invoke commit-changelog.sh (retired Step 8a path).
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

assert_not_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -qF -- "$needle"; then
        FAIL=$((FAIL + 1)); echo "FAIL: $label"
        echo "  did not expect: $needle"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    else
        PASS=$((PASS + 1)); echo "PASS: $label"
    fi
}

build_sandbox() {
    SANDBOX=$(mktemp -d "${TMPDIR:-/tmp}/larch-test-8a-changelog.XXXXXX")
    local s="$SANDBOX/scripts" r="$SANDBOX/repo" t="$SANDBOX/tmp"
    mkdir -p "$s" "$r" "$t/larch-log-batches" "$t/larch-logs/implement/run-001"

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

    cp "$REAL_FINALIZE" "$s/implement-finalize.sh"
    cp "$REAL_SCRIPTS_DIR/lib-quiet.sh" "$s/lib-quiet.sh"
    cp "$REAL_SCRIPTS_DIR/lib-execution-issues.sh" "$s/lib-execution-issues.sh"
    cp "$REAL_SCRIPTS_DIR/lib-changelog.sh" "$s/lib-changelog.sh"
    chmod +x "$s/implement-finalize.sh"

    printf '#!/usr/bin/env bash\nprintf '"'"'CHANGELOG_PRESENT=true\n'"'"'\n' > "$s/check-changelog-present.sh"
    chmod +x "$s/check-changelog-present.sh"

    cat > "$s/commit-changelog.sh" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$@" >> "$SANDBOX/commit-changelog-invocations.txt"
git add CHANGELOG.md 2>/dev/null || true
git commit -q -m "Update CHANGELOG for stub" 2>/dev/null || true
printf 'COMMITTED=true\nCOMMIT_SHA=stub\n'
STUB
    chmod +x "$s/commit-changelog.sh"

    cat > "$s/larch-log.sh" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$@" >> "$SANDBOX/larch-log-invocations.txt"
printf 'LOG_WRITTEN=true\nUNCHANGED=false\nCOMMIT_SHA=abc\n'
STUB
    chmod +x "$s/larch-log.sh"

    printf '#!/usr/bin/env bash\nprintf '"'"'SKIPPED_ALREADY_FRESH=true\n'"'"'\n' > "$s/rebase-push.sh"
    chmod +x "$s/rebase-push.sh"

    printf '#!/usr/bin/env bash\nprintf '"'"'STATE=absent\n'"'"'\n' > "$s/check-remote-branch.sh"
    chmod +x "$s/check-remote-branch.sh"

    for stub in read-session-env-key.sh token-ledger.sh timing-ledger.sh \
                token-report.sh timing-report.sh tracking-issue-write.sh; do
        printf '#!/usr/bin/env bash\nexit 0\n' > "$s/$stub"
        chmod +x "$s/$stub"
    done

    touch "$t/execution-issues.md"
}

make_state_file() {
    local manifest_path=$1
    local sf="$SANDBOX/tmp/state.sh"
    cat > "$sf" <<STATE
BRANCH_NAME=feature-test
ISSUE_NUMBER=42
PR_TITLE=Test PR
REPO=test/repo
REPO_UNAVAILABLE=false
FORKED_TARGET=false
HAS_BUMP=true
BUMP_TYPE=PATCH
NEW_VERSION=1.0.1
BUMP_REASONING_FILE=
MANIFEST_PATH=$manifest_path
TOOL_LABEL=test
RUN_ID=run-001
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

build_sandbox

MANIFEST="$SANDBOX/tmp/manifest.json"
cat > "$MANIFEST" <<'JSON'
{
  "summary_bullets_categorized": {
    "Changed": ["Would have been a changelog bullet pre-Phase-1"]
  }
}
JSON

echo
echo "Phase 1 postbump: manifest present but CHANGELOG untouched"

git -C "$SANDBOX/repo" checkout -- CHANGELOG.md 2>/dev/null || true
rm -f "$SANDBOX/commit-changelog-invocations.txt" "$SANDBOX/larch-log-invocations.txt"
state=$(make_state_file "$MANIFEST")
out=$(run_postbump "$state")
assert_contains "CHANGELOG_STATUS=skipped-phase1" "$out" "postbump reports skipped-phase1"
assert_contains "STATUS=ok" "$out" "postbump completes ok"
assert_not_contains "CHANGELOG_STATUS=updated" "$out" "postbump does not report changelog updated"
if [ -e "$SANDBOX/commit-changelog-invocations.txt" ]; then
    FAIL=$((FAIL + 1))
    echo "FAIL: commit-changelog.sh was invoked"
    sed 's/^/    /' "$SANDBOX/commit-changelog-invocations.txt"
else
    PASS=$((PASS + 1))
    echo "PASS: commit-changelog.sh not invoked"
fi
if grep -qF 'Would have been a changelog bullet' "$SANDBOX/repo/CHANGELOG.md"; then
    FAIL=$((FAIL + 1))
    echo "FAIL: CHANGELOG.md was mutated"
else
    PASS=$((PASS + 1))
    echo "PASS: CHANGELOG.md unchanged"
fi
if [ "$(git -C "$SANDBOX/repo" log --oneline | wc -l | tr -d ' ')" -ne 2 ]; then
    FAIL=$((FAIL + 1))
    echo "FAIL: unexpected commit count after postbump"
    git -C "$SANDBOX/repo" log --oneline | sed 's/^/    /'
else
    PASS=$((PASS + 1))
    echo "PASS: no extra CHANGELOG commit on branch"
fi

echo
TOTAL=$((PASS + FAIL))
echo "test-step-8a-changelog: $PASS/$TOTAL passed"
if [ "$FAIL" -gt 0 ]; then
    echo "FAILED: $FAIL test(s)" >&2
    exit 1
fi
