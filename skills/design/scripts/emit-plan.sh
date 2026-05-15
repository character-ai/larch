#!/usr/bin/env bash
# Validate and emit the /design plan diff-size sidecar.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init

DESIGN_TMPDIR=""

usage() {
    cat >&2 <<'USAGE'
usage: emit-plan.sh --design-tmpdir DIR
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "emit-plan.sh: unknown argument: $1" >&2
            usage
            exit 2
            ;;
    esac
done

if [[ -z "$DESIGN_TMPDIR" ]]; then
    echo "emit-plan.sh: --design-tmpdir is required" >&2
    usage
    exit 2
fi

PLAN_FILE="$DESIGN_TMPDIR/plan.txt"
DIFF_LINES_FILE="$DESIGN_TMPDIR/diff-lines.txt"

if [[ ! -s "$PLAN_FILE" ]]; then
    emit_kv EMIT_PLAN_STATUS missing-diff-lines
    exit 1
fi

last_line=$(awk 'NF { line=$0 } END { print line }' "$PLAN_FILE")
case "$last_line" in
    diff_lines:\ *)
        diff_lines="${last_line#diff_lines: }"
        ;;
    *)
        emit_kv EMIT_PLAN_STATUS missing-diff-lines
        exit 1
        ;;
esac

case "$diff_lines" in
    ''|*[!0-9]*)
        emit_kv EMIT_PLAN_STATUS missing-diff-lines
        exit 1
        ;;
esac

tmp=$(mktemp "${DIFF_LINES_FILE}.tmp.XXXXXX")
cleanup() {
    rm -f "$tmp"
}
trap cleanup EXIT
printf '%s\n' "$diff_lines" > "$tmp"
mv "$tmp" "$DIFF_LINES_FILE"
trap - EXIT

emit_kv EMIT_PLAN_STATUS ok
emit_kv DIFF_LINES "$diff_lines"
