#!/usr/bin/env bash
# test-larch-logs-manifest.sh — manifest schema and atomicity checks.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
LARCH_LOG="$SCRIPT_DIR/larch-log.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-larch-logs-manifest.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
export LARCH_LOG_ROOT="$TMP/larch-logs"

"$LARCH_LOG" init --skill design --run-id run999 --parent-skill implement --issue 7 >/dev/null
manifest="$LARCH_LOG_ROOT/design/run999/manifest.json"

if command -v jq >/dev/null 2>&1; then
    jq -e '
      .schema_version == 2 and
      .skill == "design" and
      .run_id == "run999" and
      .operator_cwd == "<OPERATOR_CWD>" and
      (.operator_repo_root == "<REPO_ROOT>" or .operator_repo_root == null) and
      .parent_skill == "implement" and
      .issue_number == 7 and
      (.pr_number | not) and
      (.steps_ran | type == "object") and
      (.model_roster | type == "object") and
      (.model_roster.main | type == "string" and length > 0) and
      (.flags | type == "object")
    ' "$manifest" >/dev/null
else
    grep -q '"schema_version": 2' "$manifest"
    grep -q '"skill": "design"' "$manifest"
    grep -q '"operator_cwd":' "$manifest"
    grep -q '"operator_repo_root":' "$manifest"
fi

before="$(cat "$manifest")"
"$LARCH_LOG" init --skill design --run-id run999 --parent-skill implement --issue 7 >/dev/null
after="$(cat "$manifest")"
[ "$before" = "$after" ] || {
    echo "FAIL: init retry changed manifest" >&2
    exit 1
}

before_ts="$(jq -r '.updated_at' "$manifest")"
"$LARCH_LOG" manifest --skill design --run-id run999 --field attempt=2 >/dev/null
after_ts="$(jq -r '.updated_at' "$manifest")"
after_attempt="$(jq -r '.attempt' "$manifest")"
[ "$before_ts" != "$after_ts" ] || {
    echo "FAIL: manifest cmd did not refresh updated_at" >&2
    exit 1
}
[ "$after_attempt" = "2" ] || {
    echo "FAIL: manifest cmd did not apply attempt field" >&2
    exit 1
}

leftovers="$(find "$(dirname "$manifest")" -name '.tmp.manifest.*' -print)"
[ -z "$leftovers" ] || {
    echo "FAIL: manifest temp file left behind: $leftovers" >&2
    exit 1
}

echo "All assertions passed."
