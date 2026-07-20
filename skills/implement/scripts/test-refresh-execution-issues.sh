#!/usr/bin/env bash
# test-refresh-execution-issues.sh — offline harness for refresh-execution-issues.sh.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/refresh-execution-issues.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-refresh-execution-issues.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0; FAIL=0
pass(){ PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail(){ FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)"; printf 'ACTUAL: %s\n' "$2" >&2 ;; esac; }
finish(){ [ "$FAIL" -eq 0 ] || exit 1; printf 'PASS=%s\n' "$PASS"; }

plugin="$TMP_ROOT/plugin"; mkdir -p "$plugin/scripts" "$plugin/python"
cat > "$plugin/python/cli.py" <<'STUB'
#!/usr/bin/env python3
import os
import shutil
import sys

if sys.argv[1:3] == ["plugin", "read-version"]:
    print("LARCH_PLUGIN_VERSION=1.2.3")
    raise SystemExit(0)
if sys.argv[1:3] == ["kv", "get"]:
    args = sys.argv[3:]
    source = sys.stdin.read()
    if "--file" in args:
        with open(args[args.index("--file") + 1], encoding="utf-8") as handle:
            source = handle.read()
    key = args[args.index("--key") + 1]
    for line in source.splitlines():
        if line.startswith(key + "="):
            print(line.split("=", 1)[1])
            break
    raise SystemExit(0)
if sys.argv[1:3] == ["tracking-issue", "upsert-summary"]:
    args = sys.argv[3:]
    log = os.environ.get("TRACKING_ARGS_LOG")
    if log:
        with open(log, "w", encoding="utf-8") as handle:
            handle.write(" ".join(args) + "\n")
    if "--content-file" in args:
        shutil.copyfile(args[args.index("--content-file") + 1], os.environ["TRACKING_CONTENT_LOG"])
    print("COMMENT_URL=https://example.test/comment/2")
    raise SystemExit(0)
raise SystemExit(2)
STUB
chmod +x "$plugin/python/cli.py"

# Happy path: IMPLEMENT_TMPDIR with parent-issue.md and session-env.sh
impl_dir="$TMP_ROOT/impl"; mkdir -p "$impl_dir"
printf 'ISSUE_NUMBER=3\nRUN_ID=run-2\nADOPTED=true\n' > "$impl_dir/parent-issue.md"
printf 'REPO=owner/repo\nCODER=codex\n' > "$impl_dir/session-env.sh"
cat > "$impl_dir/summary-metadata.md" <<'EOF'
Run ID: `run-2`
Run log: provider `unknown`, skill `implement`, run ID `run-2`
Tracking issue: #3
Agent: `claude`
Coder: `codex`
Larch version: `1.2.3`
EOF
cat > "$impl_dir/execution-issues.md" <<'EOF'
### Warnings

- first
- second
EOF

out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content.md" \
      "$HELPER" --implement-tmpdir "$impl_dir")
assert_contains 'REFRESHED=true' "$out" 'happy path refreshed'
assert_contains "Execution issues pending flush: \`2\`" "$(cat "$TMP_ROOT/content.md")" 'summary includes count'
assert_contains "Coder: \`codex\`" "$(cat "$TMP_ROOT/content.md")" 'existing metadata preserved'

# issue-not-set when ISSUE_NUMBER=0
impl_zero="$TMP_ROOT/impl-zero"; mkdir -p "$impl_zero"
printf 'ISSUE_NUMBER=0\nRUN_ID=run-2\n' > "$impl_zero/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_zero/session-env.sh"
skip=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --implement-tmpdir "$impl_zero")
assert_contains 'REFRESHED=true' "$skip" 'issue zero skip emits refreshed true'
assert_contains 'REASON=issue-not-set' "$skip" 'issue zero skip explains reason'

# Missing --implement-tmpdir
set +e
bad=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing arg exits non-zero'; else fail 'missing arg exits non-zero'; fi
assert_contains 'REFRESHED=false' "$bad" 'missing arg emits envelope'

finish
