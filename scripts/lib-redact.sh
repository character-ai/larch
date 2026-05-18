#!/usr/bin/env bash
# lib-redact.sh — source-able trimmers for larch log sidecars.

set -euo pipefail

larch_redact_strip_meta_cmd_json() {
    local input="$1"
    local output="$2"
    awk 'index($0, "CMD_JSON=") != 1 { print }' "$input" > "$output"
}

larch_redact_strip_json_result() {
    local input="$1"
    local output="$2"
    if command -v jq >/dev/null 2>&1; then
        if jq 'if type == "object" then del(.result) else . end' "$input" > "$output" 2>/dev/null; then
            return 0
        fi
    fi
    if command -v python3 >/dev/null 2>&1; then
        if python3 - "$input" "$output" <<'PYEOF'
import json
import sys

source, dest = sys.argv[1], sys.argv[2]
with open(source, encoding="utf-8") as fh:
    data = json.load(fh)
if isinstance(data, dict):
    data.pop("result", None)
with open(dest, "w", encoding="utf-8") as fh:
    json.dump(data, fh, separators=(",", ":"))
    fh.write("\n")
PYEOF
        then
            return 0
        fi
    fi
    cp "$input" "$output"
}

larch_redact_strip_cursor_json_result() {
    larch_redact_strip_json_result "$1" "$2"
}
