#!/usr/bin/env bash
# test-post-tracking-issue.sh — offline harness for post-tracking-issue.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
HELPER="$SCRIPT_DIR/post-tracking-issue.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-post-tracking-issue.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0
FAIL=0

pass(){ PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail(){ FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)"; printf 'ACTUAL: %s\n' "$2" >&2 ;; esac; }
finish(){ if [ "$FAIL" -ne 0 ]; then printf 'FAILURES=%s\n' "$FAIL" >&2; exit 1; fi; printf 'PASS=%s\n' "$PASS"; }

plugin="$TMP_ROOT/plugin"
mkdir -p "$plugin/scripts" "$plugin/python"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$plugin/scripts/lib-quiet.sh"
cat > "$plugin/python/cli.py" <<'STUB'
#!/usr/bin/env python3
import os
import shutil
import sys

if sys.argv[1:3] == ["plugin", "read-version"]:
    print("LARCH_PLUGIN_VERSION=9.9.9")
    raise SystemExit(0)
if sys.argv[1:3] == ["tracking-issue", "upsert-summary"]:
    args = sys.argv[3:]
    log = os.environ.get("TRACKING_ARGS_LOG")
    if log:
        with open(log, "w", encoding="utf-8") as handle:
            handle.write(" ".join(args) + "\n")
    if "--content-file" in args:
        shutil.copyfile(args[args.index("--content-file") + 1], os.environ["TRACKING_CONTENT_LOG"])
    print("COMMENT_URL=https://example.test/comment/1")
    raise SystemExit(0)
raise SystemExit(2)
STUB
chmod +x "$plugin/python/cli.py"

# Happy path: IMPLEMENT_TMPDIR with parent-issue.md and session-env.sh
impl_dir="$TMP_ROOT/impl"
mkdir -p "$impl_dir"
printf 'ISSUE_NUMBER=12\nRUN_ID=run-1\nADOPTED=true\n' > "$impl_dir/parent-issue.md"
printf 'REPO=owner/repo\nCODER=codex\n' > "$impl_dir/session-env.sh"
printf 'EMERGENCY_REQUESTED=true\n' > "$impl_dir/run-flags.sh"

out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_ARGS_LOG="$TMP_ROOT/args.log" \
      TRACKING_CONTENT_LOG="$TMP_ROOT/content.md" \
      "$HELPER" --implement-tmpdir "$impl_dir")
assert_contains 'POSTED=true' "$out" 'happy path posts'
assert_contains 'COMMENT_URL=https://example.test/comment/1' "$out" 'happy path emits URL'
assert_contains '<!-- larch:metadata v1 runid=run-1 -->' "$(cat "$TMP_ROOT/args.log")" 'marker passed'
assert_contains "Coder: \`codex\`" "$(cat "$TMP_ROOT/content.md")" 'content includes coder from session-env'
assert_contains "Larch version: \`9.9.9\`" "$(cat "$TMP_ROOT/content.md")" 'content includes version'

out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_ARGS_LOG="$TMP_ROOT/args-em.log" \
      TRACKING_CONTENT_LOG="$TMP_ROOT/content-em.md" \
      "$HELPER" --implement-tmpdir "$impl_dir" --emergency-requested true)
assert_contains 'POSTED=true' "$out" 'emergency metadata posts'
assert_contains 'Emergency: true' "$(cat "$TMP_ROOT/content-em.md")" 'emergency metadata includes line'

out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_ARGS_LOG="$TMP_ROOT/args-emf.log" \
      TRACKING_CONTENT_LOG="$TMP_ROOT/content-emf.md" \
      "$HELPER" --implement-tmpdir "$impl_dir" --emergency-requested false)
assert_contains 'POSTED=true' "$out" 'non-emergency metadata posts'
if grep -Fq 'Emergency: true' "$TMP_ROOT/content-emf.md"; then
    pass 'persisted emergency keeps line when argv false'
else
    fail 'persisted emergency keeps line when argv false'
fi

printf 'EMERGENCY_REQUESTED=false\n' > "$impl_dir/run-flags.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_ARGS_LOG="$TMP_ROOT/args-emf2.log" \
      TRACKING_CONTENT_LOG="$TMP_ROOT/content-emf2.md" \
      "$HELPER" --implement-tmpdir "$impl_dir" --emergency-requested false)
assert_contains 'POSTED=true' "$out" 'explicit false metadata posts'
if grep -Fq 'Emergency: true' "$TMP_ROOT/content-emf2.md"; then
    fail 'explicit false without persisted emergency omits line'
else
    pass 'explicit false without persisted emergency omits line'
fi

set +e
bad=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --implement-tmpdir "$impl_dir" --emergency-requested maybe 2>/dev/null)
rc=$?
set -e
if [ "$rc" -eq 2 ]; then pass 'invalid emergency flag exits 2'; else fail 'invalid emergency flag exits 2'; fi
assert_contains 'POSTED=false' "$bad" 'invalid emergency flag emits envelope'
assert_contains 'ERROR=--emergency-requested must be true or false' "$bad" 'invalid emergency flag emits validation error'

cat > "$plugin/python/cli.py" <<'STUB'
#!/usr/bin/env python3
import os
import shutil
import sys
if sys.argv[1:3] == ["tracking-issue", "upsert-summary"]:
    args = sys.argv[3:]
    log = os.environ.get("TRACKING_ARGS_LOG")
    if log:
        with open(log, "w", encoding="utf-8") as handle:
            handle.write(" ".join(args) + "\n")
    if "--content-file" in args:
        shutil.copyfile(args[args.index("--content-file") + 1], os.environ["TRACKING_CONTENT_LOG"])
    print("COMMENT_URL=https://example.test/comment/1")
    raise SystemExit(0)
raise SystemExit(2)
STUB
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_ARGS_LOG="$TMP_ROOT/args-verfail.log" \
      TRACKING_CONTENT_LOG="$TMP_ROOT/content-verfail.md" \
      "$HELPER" --implement-tmpdir "$impl_dir")
assert_contains 'POSTED=true' "$out" 'version read failure still posts'
assert_contains "Larch version: \`unknown\`" "$(cat "$TMP_ROOT/content-verfail.md")" 'version read failure falls back to unknown'

# Missing --implement-tmpdir
set +e
bad=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing --implement-tmpdir exits non-zero'; else fail 'missing --implement-tmpdir exits non-zero'; fi
assert_contains 'POSTED=false' "$bad" 'missing arg emits envelope'

finish
