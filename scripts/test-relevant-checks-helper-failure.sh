#!/usr/bin/env bash
# Regression harness for run-relevant-checks-captured.sh failure envelopes.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
HELPER="$REPO_ROOT/scripts/run-relevant-checks-captured.sh"
REDACT_TMP="$REPO_ROOT/scripts/redact-tmpdir-paths.sh"
REDACT_SECRETS="$REPO_ROOT/scripts/redact-secrets.sh"

tmp=$(mktemp -d "${TMPDIR:-/tmp}/test-relevant-checks-failure.XXXXXX")
trap 'rm -rf "$tmp"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

fixture_repo="$tmp/repo"
mkdir -p "$fixture_repo/.claude/skills/relevant-checks/scripts"
cat > "$fixture_repo/.claude/skills/relevant-checks/scripts/run-checks.sh" <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
echo "=== Running pre-commit on 1 changed file(s) ==="
echo "secret AKIA1234567890ABCDEF and ghp_123456789012345678901234567890123456"
echo "tmp path /tmp/larch-implement-demo"
echo "=== Running agent-lint ==="
echo "agent-lint failure"
exit 1
SCRIPT
chmod +x "$fixture_repo/.claude/skills/relevant-checks/scripts/run-checks.sh"

xdg="$tmp/cache"
session="$xdg/larch/sessions/claude-implement-repo-FAIL"
mkdir -p "$session"

rc=0
out=$(XDG_CACHE_HOME="$xdg" CLAUDE_PROJECT_DIR="$fixture_repo" "$HELPER" --site step3 --tmpdir "$session") || rc=$?
[[ "$rc" -eq 1 ]] || fail "expected passthrough rc 1, got $rc"
for token in 'STATUS=fail' 'EXIT_CODE=1' 'LOG_FILE=' 'REDACTED_LOG_FILE=' 'LOG_BYTES=' 'PHASE=agent-lint'; do
    [[ "$out" == *"$token"* ]] || fail "missing token $token in: $out"
done

log_file=$(printf '%s\n' "$out" | awk -F= '$1=="LOG_FILE"{print substr($0,index($0,"=")+1)}')
redacted_file=$(printf '%s\n' "$out" | awk -F= '$1=="REDACTED_LOG_FILE"{print substr($0,index($0,"=")+1)}')
[[ -f "$log_file" ]] || fail "raw log missing"
[[ -f "$redacted_file" ]] || fail "redacted log missing"
grep -q 'AKIA1234567890ABCDEF' "$log_file" || fail "raw log did not retain synthetic token"
! grep -q 'AKIA1234567890ABCDEF' "$redacted_file" || fail "redacted log leaked AWS-shaped token"
! grep -q 'ghp_123456789012345678901234567890123456' "$redacted_file" || fail "redacted log leaked GitHub-shaped token"
! grep -q '/tmp/larch-implement-demo' "$redacted_file" || fail "redacted log leaked tmp path"

# Simulate redaction-failed by running the helper from a fixture scripts/
# directory where the redactor copies are non-executable. Never chmod the
# tracked redactor in the repo working tree (issue #1543 review FINDING_5: a
# SIGKILL between chmod and trap restoration would leave the repo dirty and
# break subsequent helper invocations elsewhere).
fixture_scripts="$tmp/fixture-scripts"
mkdir -p "$fixture_scripts"
cp "$HELPER" "$fixture_scripts/run-relevant-checks-captured.sh"
chmod +x "$fixture_scripts/run-relevant-checks-captured.sh"
cp "$REDACT_TMP" "$fixture_scripts/redact-tmpdir-paths.sh"
cp "$REDACT_SECRETS" "$fixture_scripts/redact-secrets.sh"
chmod a-x "$fixture_scripts/redact-tmpdir-paths.sh" "$fixture_scripts/redact-secrets.sh"
rc=0
out=$(XDG_CACHE_HOME="$xdg" CLAUDE_PROJECT_DIR="$fixture_repo" "$fixture_scripts/run-relevant-checks-captured.sh" --site redaction --tmpdir "$session") || rc=$?
[[ "$rc" -eq 1 ]] || fail "redaction-failed path expected rc 1, got $rc"
[[ "$out" == "STATUS=fail FAILURE_REASON=redaction-failed" ]] || fail "redaction failure stdout mismatch: $out"
[[ "$out" != *"LOG_FILE="* ]] || fail "redaction failure leaked raw log path"

echo "test-relevant-checks-helper-failure: ok"
