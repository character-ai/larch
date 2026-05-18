#!/usr/bin/env bash
# test-refresh-execution-issues.sh — offline harness for refresh-execution-issues.sh.
# shellcheck disable=SC2016

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
HELPER="$SCRIPT_DIR/refresh-execution-issues.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-refresh-execution-issues.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0; FAIL=0
pass(){ PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail(){ FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)" ;; esac; }
finish(){ [ "$FAIL" -eq 0 ] || exit 1; printf 'PASS=%s\n' "$PASS"; }

plugin="$TMP_ROOT/plugin"; mkdir -p "$plugin/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$plugin/scripts/lib-quiet.sh"
cat > "$plugin/scripts/read-plugin-version.sh" <<'STUB'
#!/usr/bin/env bash
printf 'LARCH_PLUGIN_VERSION=1.2.3\n'
STUB
cat > "$plugin/scripts/tracking-issue-summary.sh" <<'STUB'
#!/usr/bin/env bash
while [ $# -gt 0 ]; do case "$1" in --content-file) cp "$2" "${TRACKING_CONTENT_LOG:?}"; shift 2 ;; *) shift ;; esac; done
printf 'COMMENT_URL=https://example.test/comment/2\n'
STUB
chmod +x "$plugin/scripts/read-plugin-version.sh" "$plugin/scripts/tracking-issue-summary.sh"

session="$TMP_ROOT/session"; mkdir -p "$session"; printf 'REPO=owner/repo\n' > "$session/session-env.sh"
cat > "$session/summary-metadata.md" <<'EOF'
Run ID: `run-2`
Logs: `larch-logs/implement/run-2/`
Tracking issue: #3
Agent: `claude`
Coder: `codex`
Larch version: `1.2.3`
EOF
cat > "$session/execution-issues.md" <<'EOF'
### Warnings

- first
- second
EOF
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content.md" "$HELPER" --issue 3 --run-id run-2 --session-env "$session/session-env.sh" --implement-tmpdir "$session")
assert_contains 'REFRESHED=true' "$out" 'happy path refreshed'
assert_contains 'Execution issues pending flush: `2`' "$(cat "$TMP_ROOT/content.md")" 'summary includes count'
assert_contains 'Coder: `codex`' "$(cat "$TMP_ROOT/content.md")" 'existing metadata preserved'

skip=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --issue 0 --run-id run-2 --session-env "$session/session-env.sh" --implement-tmpdir "$session")
assert_contains 'REFRESHED=true' "$skip" 'issue zero skip emits refreshed true'
assert_contains 'REASON=issue-not-set' "$skip" 'issue zero skip explains reason'

set +e
bad=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --issue x 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'bad args exit non-zero'; else fail 'bad args exit non-zero'; fi
assert_contains 'REFRESHED=false' "$bad" 'bad args emits envelope'

finish
