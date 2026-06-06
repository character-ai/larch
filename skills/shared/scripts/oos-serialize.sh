#!/usr/bin/env bash
# oos-serialize.sh — Serialize accepted out-of-scope review observations.

set -euo pipefail

usage() { echo "Usage: oos-serialize.sh --findings-file FILE --output-file FILE [--session-env-path FILE]" >&2; }

FINDINGS_FILE=""
OUTPUT_FILE=""
SESSION_ENV_PATH=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --findings-file) FINDINGS_FILE="${2:?--findings-file requires a value}"; shift 2 ;;
        --output-file) OUTPUT_FILE="${2:?--output-file requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "oos-serialize.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

[[ -n "$FINDINGS_FILE" && -f "$FINDINGS_FILE" ]] || { echo "oos-serialize.sh: --findings-file must name a file" >&2; exit 2; }
[[ -n "$OUTPUT_FILE" ]] || { echo "oos-serialize.sh: --output-file is required" >&2; exit 2; }
mkdir -p "$(dirname "$OUTPUT_FILE")"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
NORMALIZE_OOS_HELPER="$DIR/normalize-oos-block-header.sh"
TMPDIR_OOS=$(mktemp -d "${TMPDIR:-/tmp}/larch-oos-serialize.XXXXXX")
cleanup() { rm -rf "$TMPDIR_OOS"; }
trap cleanup EXIT

is_security_tagged_block() {
    local block="$1"
    command -v python3 >/dev/null 2>&1 || {
        echo "oos-serialize.sh: python3 is required for security classification" >&2
        return 2
    }
    python3 -c 'import re, sys' >/dev/null 2>&1 || {
        echo "oos-serialize.sh: python3 security classifier smoke test failed" >&2
        return 2
    }
    python3 - "$block" <<'PYEOF'
import re
import sys

try:
    text = open(sys.argv[1], encoding="utf-8").read()
except OSError as exc:
    print(f"oos-serialize.sh: security classifier read failed: {exc}", file=sys.stderr)
    sys.exit(2)
text_no_fence = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
text_no_backtick = re.sub(r"`[^`\n]*`", "", text_no_fence)
canonical_token = re.compile(r"focus-area\s*=\s*security", re.IGNORECASE)
explicit_header = re.compile(
    r"^###\s+(?:OOS_\d+:|FINDING_\d+:)\s*(?:\[(?:OUT_OF_SCOPE|OOS)\]\s*)?"
    r"`?(?:\[security\]|<security>)`?(?:\s|$|[:-])",
    re.IGNORECASE,
)
field_value = re.compile(
    r"^[ \t-]*focus-area[ \t]*[:=][ \t]*security(?:[-a-z0-9 _]*)(?:[ \t]|$|\(|#|\.|,)",
    re.IGNORECASE,
)
found = bool(canonical_token.search(text_no_backtick))
lines = text_no_fence.splitlines()
if not found and lines and explicit_header.search(lines[0]):
    found = True
if not found:
    for line in lines:
        normalized = line.replace("`", "").replace("*", "").strip()
        if field_value.search(normalized):
            found = True
            break
sys.exit(0 if found else 1)
PYEOF
}

flush_block() {
    [[ "$in_block" == "1" ]] || return 0
    if [[ "$oos" != "1" ]]; then
        return 0
    fi
    block_file="$TMPDIR_OOS/block.md"
    printf '%s' "$block" > "$block_file"
    local sec_rc=0
    is_security_tagged_block "$block_file" || sec_rc=$?
    if [[ "$sec_rc" -eq 0 ]]; then
        held=$((held + 1))
    elif [[ "$sec_rc" -ne 1 ]]; then
        exit 2
    elif awk 'BEGIN { found=0; accepted=0 } /^Vote tally: / && /(^|[[:space:]])Result=/ { found=1; if ($0 ~ /(^|[[:space:]])Result=accepted([[:space:]]|$)/) accepted=1 } END { exit (found && !accepted) ? 1 : 0 }' "$block_file"; then
        seq=$((seq + 1))
        "$NORMALIZE_OOS_HELPER" --seq "$seq" --block-file "$block_file" >> "$OUTPUT_FILE"
        printf '\n' >> "$OUTPUT_FILE"
        accepted=$((accepted + 1))
    fi
}

: > "$OUTPUT_FILE"
in_block=0
block=""
oos=0
seq=0
accepted=0
held=0

while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^###[[:space:]]+FINDING_[0-9]+: ]]; then
        flush_block
        in_block=1
        block="${line}"$'\n'
        oos=0
        if [[ "$line" == *"[OUT_OF_SCOPE]"* || "$line" == *"[OOS]"* ]]; then
            oos=1
        fi
        continue
    fi
    if [[ "$in_block" == "1" ]]; then
        block+="${line}"$'\n'
        if [[ "$line" == *"[OUT_OF_SCOPE]"* || "$line" == *"[OOS]"* ]]; then
            oos=1
        fi
    fi
done < "$FINDINGS_FILE"
flush_block

printf 'OOS_ACCEPTED=%d\nOOS_HELD_SECURITY=%d\n' "$accepted" "$held"
: "$SESSION_ENV_PATH"
