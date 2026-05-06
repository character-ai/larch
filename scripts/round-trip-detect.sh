#!/usr/bin/env bash
# round-trip-detect.sh — side-effect-free detector for work undo/redo markers.

set -euo pipefail

PATTERNS='(^|[^[:alnum:]_])was reverted in [0-9a-f]{7,40}([^[:alnum:]_]|$)|(^|[^[:alnum:]_])re-?introduce([^[:alnum:]_]|$)|(^|[^[:alnum:]_])re-?add([^[:alnum:]_]|$)|(^|[^[:alnum:]_])revert of #[0-9]+([^[:alnum:]_]|$)|(^|[^[:alnum:]_])revert of [0-9a-f]{7,40}([^[:alnum:]_]|$)|(^|[^[:alnum:]_])closed in favor of #[0-9]+([^[:alnum:]_]|$)|(^|[^[:alnum:]_])replace standalone with alias([^[:alnum:]_]|$)'

warn_false() {
    printf 'round-trip-detect.sh: warning: %s\n' "$1" >&2
    echo "ROUND_TRIP=false"
    exit 0
}

HAYSTACK=""
ADD_STDIN=false

while [ $# -gt 0 ]; do
    case "$1" in
        --text-file)
            [ $# -ge 2 ] || warn_false "--text-file requires a value"
            [ -f "$2" ] || warn_false "text file not found: $2"
            HAYSTACK="${HAYSTACK}"$'\n'"$(cat "$2")"
            shift 2
            ;;
        --text-string)
            [ $# -ge 2 ] || warn_false "--text-string requires a value"
            HAYSTACK="${HAYSTACK}"$'\n'"$2"
            shift 2
            ;;
        --stdin)
            ADD_STDIN=true
            shift
            ;;
        --help)
            cat <<'USAGE'
Usage:
  round-trip-detect.sh [--text-file PATH ...] [--text-string STR ...] [--stdin]
USAGE
            exit 0
            ;;
        *)
            warn_false "unknown option: $1"
            ;;
    esac
done

if [ "$ADD_STDIN" = "true" ]; then
    HAYSTACK="${HAYSTACK}"$'\n'"$(cat)"
fi

HAYSTACK=$(printf '%s' "$HAYSTACK" | tr '[:upper:]' '[:lower:]') || warn_false "failed to normalize input"

if printf '%s' "$HAYSTACK" | grep -qiE "$PATTERNS"; then
    echo "ROUND_TRIP=true"
else
    echo "ROUND_TRIP=false"
fi

exit 0
