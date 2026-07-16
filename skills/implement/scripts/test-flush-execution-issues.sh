#!/usr/bin/env bash
# Delegation smoke for flush-execution-issues.sh.
# Behavioral coverage lives in python/tests/issue/test_execution_issues.py.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/flush-execution-issues.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-flush-execution-issues.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

write_cli() {
    local root=$1
    mkdir -p "$root/python"
    cat >"$root/python/cli.py" <<'PY'
import json
import os
import sys
from pathlib import Path

Path(os.environ["FLUSH_CAPTURE"]).write_text(json.dumps({"program": sys.argv[0], "argv": sys.argv[1:]}), encoding="utf-8")
sys.stdout.write("wrapper stdout\n")
sys.stderr.write("wrapper stderr\n")
raise SystemExit(23)
PY
}

assert_case() {
    local helper=$1 root=$2 capture=$3 stdout=$4 stderr=$5 plugin_root=$2 rc
    if [ "$helper" = "$fallback/skills/implement/scripts/flush-execution-issues.sh" ]; then plugin_root=""; fi
    set +e
    CLAUDE_PLUGIN_ROOT="$plugin_root" FLUSH_CAPTURE="$capture" "$helper" --run-id run-7 --issue-log 'two words' >"$stdout" 2>"$stderr"
    rc=$?
    set -e
    [ "$rc" -eq 23 ] && [ "$(cat "$stdout")" = 'wrapper stdout' ] && [ "$(cat "$stderr")" = 'wrapper stderr' ]
    python3 - "$capture" "$root" <<'PY'
import json
import sys
from pathlib import Path

record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if Path(record["program"]).resolve() != (Path(sys.argv[2]) / "python" / "cli.py").resolve() or record["argv"] != ["execution-issues", "flush", "--run-id", "run-7", "--issue-log", "two words"]:
    raise SystemExit(f"unexpected delegation: {record!r}")
PY
}

fallback="$TMP_ROOT/fallback"; mkdir -p "$fallback/skills/implement/scripts"
cp "$HELPER" "$fallback/skills/implement/scripts/flush-execution-issues.sh"
chmod +x "$fallback/skills/implement/scripts/flush-execution-issues.sh"
write_cli "$fallback"
assert_case "$fallback/skills/implement/scripts/flush-execution-issues.sh" "$fallback" "$TMP_ROOT/fallback.json" "$TMP_ROOT/fallback.out" "$TMP_ROOT/fallback.err"

override="$TMP_ROOT/override"; write_cli "$override"
assert_case "$HELPER" "$override" "$TMP_ROOT/override.json" "$TMP_ROOT/override.out" "$TMP_ROOT/override.err"
printf 'PASS: flush-execution-issues wrapper delegation\n'
