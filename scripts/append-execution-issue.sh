#!/usr/bin/env bash
# append-execution-issue.sh — append a categorized execution issue entry.

set -euo pipefail

fail_usage() {
    echo "FAILED=true"
    echo "ERROR=usage: $1"
    exit 1
}

LOG_FILE=""
CATEGORY=""
ENTRY=""

while [ $# -gt 0 ]; do
    case "$1" in
        --log)
            [ $# -ge 2 ] || fail_usage "--log requires a value"
            LOG_FILE="$2"; shift 2 ;;
        --category)
            [ $# -ge 2 ] || fail_usage "--category requires a value"
            CATEGORY="$2"; shift 2 ;;
        --entry)
            [ $# -ge 2 ] || fail_usage "--entry requires a value"
            ENTRY="$2"; shift 2 ;;
        *)
            fail_usage "unknown flag: $1" ;;
    esac
done

[ -n "$LOG_FILE" ] || fail_usage "--log is required"
[ -n "$CATEGORY" ] || fail_usage "--category is required"
[ -n "$ENTRY" ] || fail_usage "--entry is required"

case "$CATEGORY" in
    "Pre-existing Code Issues"|"Tool Failures"|"Permission Prompts"|"External Reviewer Issues"|"CI Issues"|"Warnings"|"Q/A") ;;
    *) fail_usage "unsupported category: $CATEGORY" ;;
esac

mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || {
    echo "FAILED=true"
    echo "ERROR=cannot create log parent: $(dirname "$LOG_FILE")"
    exit 2
}

if [ ! -f "$LOG_FILE" ]; then
    : > "$LOG_FILE" || {
        echo "FAILED=true"
        echo "ERROR=cannot create log: $LOG_FILE"
        exit 2
    }
fi

entry_tmp="$(mktemp "${LOG_FILE}.entry.XXXXXX")" || {
    echo "FAILED=true"
    echo "ERROR=cannot create temp entry file next to log"
    exit 2
}

printf '%s\n' "$ENTRY" > "$entry_tmp" || {
    echo "FAILED=true"
    echo "ERROR=cannot stage entry"
    rm -f "$entry_tmp"
    exit 2
}

tmp="$(mktemp "${LOG_FILE}.XXXXXX")" || {
    echo "FAILED=true"
    echo "ERROR=cannot create temp file next to log"
    rm -f "$entry_tmp"
    exit 2
}
trap 'rm -f "$tmp" "$entry_tmp"' EXIT

awk -v category="$CATEGORY" -v entry_file="$entry_tmp" '
    function print_entry(    line) {
        while ((getline line < entry_file) > 0) {
            print line
        }
        close(entry_file)
    }
    BEGIN {
        header = "### " category
        found = 0
        inserted = 0
    }
    $0 == header {
        found = 1
        in_target = 1
        print
        next
    }
    in_target && /^### / {
        if (!inserted) {
            print ""
            print_entry()
            inserted = 1
        }
        in_target = 0
    }
    { print }
    END {
        if (found && !inserted) {
            print ""
            print_entry()
        } else if (!found) {
            if (NR > 0) print ""
            print header
            print ""
            print_entry()
        }
    }
' "$LOG_FILE" > "$tmp" || {
    echo "FAILED=true"
    echo "ERROR=failed to update log: $LOG_FILE"
    exit 2
}

mv -f "$tmp" "$LOG_FILE" || {
    echo "FAILED=true"
    echo "ERROR=failed to move log into place: $LOG_FILE"
    exit 2
}
trap - EXIT
rm -f "$entry_tmp"

echo "APPENDED=true"
echo "LOG=$LOG_FILE"
exit 0
