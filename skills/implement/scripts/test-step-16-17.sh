#!/usr/bin/env bash
# test-step-16-17.sh — offline harness for step-16-17.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-step-16-17.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains() { case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)"; printf 'ACTUAL: %s\n' "$2" >&2 ;; esac; }
assert_not_contains() { case "$2" in *"$1"*) fail "$3 (unexpected $1)" ;; *) pass "$3" ;; esac; }
assert_file_exists() {
    if [ -e "$1" ]; then
        pass "$2"
    else
        fail "$2 (missing $1)"
    fi
}
assert_file_absent() {
    if [ ! -e "$1" ]; then
        pass "$2"
    else
        fail "$2 (present $1)"
    fi
}
assert_equals() {
    if [ "$1" = "$2" ]; then
        pass "$3"
    else
        fail "$3"
        printf 'EXPECTED: %s\nACTUAL: %s\n' "$1" "$2" >&2
    fi
}

finish() {
    [ "$FAIL" -eq 0 ] || exit 1
    printf 'PASS=%s\n' "$PASS"
}

build_plugin() {
    local plugin=$1
    mkdir -p "$plugin/skills/implement/scripts" "$plugin/python"
    cp "$REPO_ROOT/skills/implement/scripts/step-16-17.sh" "$plugin/skills/implement/scripts/step-16-17.sh"
    cp "$REPO_ROOT/skills/implement/scripts/step-16.sh" "$plugin/skills/implement/scripts/step-16.sh"
    cp "$REPO_ROOT/skills/implement/scripts/step-17.sh" "$plugin/skills/implement/scripts/step-17.sh"
    chmod +x "$plugin/skills/implement/scripts/step-16-17.sh" "$plugin/skills/implement/scripts/step-16.sh" "$plugin/skills/implement/scripts/step-17.sh"
    cat > "$plugin/python/cli.py" <<'PY'
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

args = sys.argv[1:]

def value(flag: str, default: str = "") -> str:
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            return args[idx + 1]
    return default

def append_failure() -> int:
    log = Path(value("--log"))
    output_file = Path(value("--output-file"))
    category = value("--category")
    site = value("--site")
    exit_code = value("--exit-code")
    redacted = "--redact" in args
    body = output_file.read_text(encoding="utf-8") if output_file.is_file() else ""
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"CATEGORY={category}\nSITE={site}\nEXIT={exit_code}\nREDACT={redacted}\n{body}\n")
    return 0

if args[:2] == ["session", "read-key"]:
    print(value("--default"))
    raise SystemExit(0)
if args[:2] == ["timing", "telemetry-mark"]:
    raise SystemExit(0)
if args[:2] == ["review-and-fix", "write-rejected"]:
    if os.environ.get("STEP16_FAIL") == "true":
        print("STATUS=failed")
        raise SystemExit(9)
    print("STATUS=skipped")
    raise SystemExit(0)
if args[:2] == ["slack", "issue-announce"]:
    status = os.environ.get("SLACK_STATUS") or "skipped"
    print(f"STATUS={status}")
    if status == "failed":
        print("ERROR=webhook rejected token SECRET_SHOULD_REDACT")
    else:
        print("REASON=webhook-not-set")
    raise SystemExit(int(os.environ.get("SLACK_RC") or "0"))
if args[:2] == ["run-log", "append-failure"]:
    raise SystemExit(append_failure())
if args[:2] == ["final-report", "write"]:
    impl = Path(value("--implement-tmpdir"))
    summary = impl / "summary-final.md"
    mode = os.environ.get("STEP17_MODE") or "success"
    body = os.environ.get("SUMMARY_BODY") or "## /implement run demo — succeeded\n\n- **Cost**: Claude $1, Codex $0, Cursor $0\n"
    if mode == "success":
        summary.write_text(body, encoding="utf-8")
        if "--print-stdout" in args:
            print(body, end="")
        raise SystemExit(0)
    if mode == "fail-upsert":
        summary.write_text(body, encoding="utf-8")
        print("tracking upsert failed", file=sys.stderr)
        raise SystemExit(7)
    if mode == "fail-empty":
        summary.write_text("", encoding="utf-8")
        print("render failed before body", file=sys.stderr)
        raise SystemExit(7)
    print("render failed before body", file=sys.stderr)
    raise SystemExit(7)
print("unexpected cli argv: " + " ".join(args), file=sys.stderr)
raise SystemExit(99)
PY
    chmod +x "$plugin/python/cli.py"
}

new_impl() {
    local dir=$1 plugin=$2
    mkdir -p "$dir"
    printf 'CLAUDE_PLUGIN_ROOT=%s\n' "$plugin" > "$dir/plugin-root.env"
    printf 'ISSUE_NUMBER=9\nRUN_ID=run-1\n' > "$dir/parent-issue.md"
    printf 'PR_URL=https://example.test/pr/1\nPR_TITLE=Demo\n' > "$dir/ship-pr-state.sh"
}

extract_body() {
    awk '
        $0 == "---LARCH-SUMMARY-FINAL-BEGIN---" { in_body=1; next }
        $0 == "---LARCH-SUMMARY-FINAL-END---" { exit }
        in_body { print }
    ' "$1"
}

run_wrapper() {
    local impl=$1 plugin=$2 out=$3
    set +e
    STEP16_FAIL="${STEP16_FAIL:-}" SLACK_STATUS="${SLACK_STATUS:-}" SLACK_RC="${SLACK_RC:-}" STEP17_MODE="${STEP17_MODE:-}" SUMMARY_BODY="${SUMMARY_BODY:-}" IMPLEMENT_TMPDIR="$impl" CLAUDE_PLUGIN_ROOT="$plugin" "$plugin/skills/implement/scripts/step-16-17.sh" > "$out" 2>&1
    rc=$?
    set -e
    return "$rc"
}

plugin="$TMP_ROOT/plugin"
build_plugin "$plugin"

impl="$TMP_ROOT/happy"
new_impl "$impl" "$plugin"
out="$TMP_ROOT/happy.out"
run_wrapper "$impl" "$plugin" "$out" || fail 'happy wrapper exits 0'
assert_equals 1 "$(grep -c '^---LARCH-SUMMARY-FINAL-BEGIN---$' "$out")" 'happy begin marker count'
assert_equals 1 "$(grep -c '^---LARCH-SUMMARY-FINAL-END---$' "$out")" 'happy end marker count'
extract_body "$out" > "$TMP_ROOT/happy.body"
printf '\n' >> "$TMP_ROOT/happy.body"
assert_equals "$(cat "$impl/summary-final.md")" "$(cat "$TMP_ROOT/happy.body")" 'marker body equals summary-final.md'
assert_file_exists "$impl/.step17-printed" '.step17-printed written after body'
assert_file_absent "$impl/.step17-emitted" '.step17-emitted remains orchestrator-owned'

impl="$TMP_ROOT/step16-fails"
new_impl "$impl" "$plugin"
out="$TMP_ROOT/step16-fails.out"
STEP16_FAIL=true
run_wrapper "$impl" "$plugin" "$out" || fail 'step16 failure wrapper exits 0'
unset STEP16_FAIL
assert_contains '---LARCH-SUMMARY-FINAL-BEGIN---' "$(cat "$out")" 'step16 failure still reaches markers'

impl="$TMP_ROOT/slack-skipped"
new_impl "$impl" "$plugin"
out="$TMP_ROOT/slack-skipped.out"
SLACK_STATUS=skipped
run_wrapper "$impl" "$plugin" "$out" || fail 'slack skipped wrapper exits 0'
unset SLACK_STATUS
assert_file_absent "$impl/execution-issues.md" 'slack skipped does not append warnings'

impl="$TMP_ROOT/slack-failed"
new_impl "$impl" "$plugin"
out="$TMP_ROOT/slack-failed.out"
SLACK_STATUS=failed
run_wrapper "$impl" "$plugin" "$out" || fail 'slack failed wrapper exits 0'
unset SLACK_STATUS
issues="$(cat "$impl/execution-issues.md")"
assert_contains 'CATEGORY=Warnings' "$issues" 'slack failed appends Warnings'
assert_contains 'REDACT=True' "$issues" 'slack warning uses --redact'
assert_contains '---LARCH-SUMMARY-FINAL-BEGIN---' "$(cat "$out")" 'slack failed still reaches final report'

impl="$TMP_ROOT/stale"
new_impl "$impl" "$plugin"
printf 'stale body\n' > "$impl/summary-final.md"
out="$TMP_ROOT/stale.out"
STEP17_MODE=fail-stale
run_wrapper "$impl" "$plugin" "$out" || fail 'stale failure wrapper exits 0'
unset STEP17_MODE
assert_not_contains '---LARCH-SUMMARY-FINAL-BEGIN---' "$(cat "$out")" 'stale failure prints no marker'
assert_file_absent "$impl/.step17-printed" 'stale failure does not touch printed sentinel'
assert_contains 'CATEGORY=Tool Failures' "$(cat "$impl/execution-issues.md")" 'stale failure logs Tool Failures'

impl="$TMP_ROOT/upsert"
new_impl "$impl" "$plugin"
printf 'old body\n' > "$impl/summary-final.md"
out="$TMP_ROOT/upsert.out"
STEP17_MODE=fail-upsert
SUMMARY_BODY='fresh body
'
run_wrapper "$impl" "$plugin" "$out" || fail 'upsert failure wrapper exits 0'
unset STEP17_MODE SUMMARY_BODY
assert_contains 'CATEGORY=Tool Failures' "$(cat "$impl/execution-issues.md")" 'upsert failure logs Tool Failures'
assert_contains '---LARCH-SUMMARY-FINAL-BEGIN---' "$(cat "$out")" 'upsert failure emits markers after refresh'
assert_file_exists "$impl/.step17-printed" 'upsert failure touches printed sentinel after markers'

impl="$TMP_ROOT/empty"
new_impl "$impl" "$plugin"
out="$TMP_ROOT/empty.out"
STEP17_MODE=fail-empty
run_wrapper "$impl" "$plugin" "$out" || fail 'empty failure wrapper exits 0'
unset STEP17_MODE
assert_not_contains '---LARCH-SUMMARY-FINAL-BEGIN---' "$(cat "$out")" 'empty failure prints no marker'
assert_file_absent "$impl/.step17-printed" 'empty failure does not touch printed sentinel'

finish
