#!/usr/bin/env bash
# Delegation smoke for write-final-report.sh.
# Behavioral coverage lives in python/tests/report/test_final_report.py.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/write-final-report.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-write-final-report.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

write_cli() {
    local root=$1
    mkdir -p "$root/python"
    cat >"$root/python/cli.py" <<'PY'
import json, os, sys
from pathlib import Path
Path(os.environ["WFR_CAPTURE"]).write_text(json.dumps({"program": sys.argv[0], "argv": sys.argv[1:]}), encoding="utf-8")
sys.stdout.write("wrapper stdout\n"); sys.stderr.write("wrapper stderr\n"); raise SystemExit(23)
PY
}

assert_case() {
    local helper=$1 root=$2 capture=$3 stdout=$4 stderr=$5 plugin_root=$2 rc
    if [ "$helper" = "$fallback/skills/implement/scripts/write-final-report.sh" ]; then plugin_root=""; fi
    set +e
    CLAUDE_PLUGIN_ROOT="$plugin_root" WFR_CAPTURE="$capture" \
        "$helper" --implement-tmpdir "$TMP_ROOT/impl" --comment-only >"$stdout" 2>"$stderr"
    rc=$?
    set -e
    [ "$rc" -eq 23 ] && [ "$(cat "$stdout")" = 'wrapper stdout' ] && [ "$(cat "$stderr")" = 'wrapper stderr' ]
    python3 - "$capture" "$root" "$TMP_ROOT/impl" <<'PY'
import json, sys
from pathlib import Path
record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if Path(record["program"]).resolve() != (Path(sys.argv[2]) / "python" / "cli.py").resolve() or record["argv"] != ["final-report", "write", "--implement-tmpdir", sys.argv[3], "--comment-only"]:
    raise SystemExit(f"unexpected delegation: {record!r}")
PY
}

fallback="$TMP_ROOT/fallback"; mkdir -p "$fallback/skills/implement/scripts"
cp "$HELPER" "$fallback/skills/implement/scripts/write-final-report.sh"
chmod +x "$fallback/skills/implement/scripts/write-final-report.sh"
write_cli "$fallback"
assert_case "$fallback/skills/implement/scripts/write-final-report.sh" "$fallback" "$TMP_ROOT/fallback.json" "$TMP_ROOT/fallback.out" "$TMP_ROOT/fallback.err"

override="$TMP_ROOT/override"; write_cli "$override"
assert_case "$HELPER" "$override" "$TMP_ROOT/override.json" "$TMP_ROOT/override.out" "$TMP_ROOT/override.err"
printf 'PASS: write-final-report wrapper delegation\n'
