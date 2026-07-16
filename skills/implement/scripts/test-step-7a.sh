#!/usr/bin/env bash
# test-step-7a.sh — delegation smoke for step-7a.sh.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/step-7a.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-step-7a.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

write_cli() {
    local root=$1
    mkdir -p "$root/python"
    cat >"$root/python/cli.py" <<'PY'
import json
import os
import sys
from pathlib import Path

Path(os.environ["STEP7A_CAPTURE"]).write_text(json.dumps({"program": sys.argv[0], "argv": sys.argv[1:]}), encoding="utf-8")
sys.stdout.write("wrapper stdout\n")
sys.stderr.write("wrapper stderr\n")
raise SystemExit(23)
PY
}

assert_case() {
    local helper=$1 root=$2 capture=$3 stdout=$4 stderr=$5 plugin_root=$2 rc
    if [ "$helper" = "$fallback/skills/implement/scripts/step-7a.sh" ]; then
        plugin_root=""
    fi
    set +e
    CLAUDE_PLUGIN_ROOT="$plugin_root" STEP7A_CAPTURE="$capture" "$helper" --label 'two words' >"$stdout" 2>"$stderr"
    rc=$?
    set -e
    [ "$rc" -eq 23 ]
    [ "$(cat "$stdout")" = 'wrapper stdout' ]
    [ "$(cat "$stderr")" = 'wrapper stderr' ]
    python3 - "$capture" "$root" <<'PY'
import json
import sys
from pathlib import Path

record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected_program = Path(sys.argv[2]) / "python" / "cli.py"
expected_argv = ["implement", "step-7a", "--label", "two words"]
if Path(record["program"]).resolve() != expected_program.resolve() or record["argv"] != expected_argv:
    raise AssertionError((record, str(expected_program), expected_argv))
PY
}

fallback="$TMP_ROOT/fallback"
mkdir -p "$fallback/skills/implement/scripts"
cp "$HELPER" "$fallback/skills/implement/scripts/step-7a.sh"
chmod +x "$fallback/skills/implement/scripts/step-7a.sh"
write_cli "$fallback"
assert_case "$fallback/skills/implement/scripts/step-7a.sh" "$fallback" "$TMP_ROOT/fallback.json" "$TMP_ROOT/fallback.out" "$TMP_ROOT/fallback.err"

override="$TMP_ROOT/override"
write_cli "$override"
assert_case "$HELPER" "$override" "$TMP_ROOT/override.json" "$TMP_ROOT/override.out" "$TMP_ROOT/override.err"

printf 'PASS: step-7a wrapper delegation\n'
