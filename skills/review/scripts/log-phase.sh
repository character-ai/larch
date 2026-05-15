#!/usr/bin/env bash
# log-phase.sh — Write a registered review larch-log batch.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() { echo "Usage: log-phase.sh --run-id ID --batch SLUG --action write|append --payload-file FILE [--log-root DIR]" >&2; }

RUN_ID=""
BATCH=""
ACTION=""
PAYLOAD_FILE=""
LOG_ROOT="${LARCH_LOG_ROOT:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
        --batch) BATCH="${2:?--batch requires a value}"; shift 2 ;;
        --action) ACTION="${2:?--action requires a value}"; shift 2 ;;
        --payload-file) PAYLOAD_FILE="${2:?--payload-file requires a value}"; shift 2 ;;
        --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "log-phase.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

[[ -n "$RUN_ID" && -n "$BATCH" && -n "$ACTION" && -n "$PAYLOAD_FILE" ]] || { usage; exit 2; }
[[ "$ACTION" == "write" || "$ACTION" == "append" ]] || { echo "log-phase.sh: --action must be write or append" >&2; exit 2; }
[[ -f "$PAYLOAD_FILE" ]] || { echo "log-phase.sh: --payload-file must name a file" >&2; exit 2; }

case "$BATCH" in
    review-context|review-panel-manifest|review-findings|review-tally|review-round-summary) ;;
    *) echo "log-phase.sh: unregistered review batch: $BATCH" >&2; exit 2 ;;
esac

args=(--skill review --run-id "$RUN_ID" --batch "$BATCH")
[[ -n "$LOG_ROOT" ]] && args=(--log-root "$LOG_ROOT" "${args[@]}")
log_phase_stdout=$(mktemp "${TMPDIR:-/tmp}/review-log-phase.XXXXXX") || exit 1
trap 'rm -f "$log_phase_stdout"' EXIT
if [[ "$ACTION" == "write" ]]; then
    "$PLUGIN_ROOT/scripts/larch-log.sh" write "${args[@]}" --input-file "$PAYLOAD_FILE" > "$log_phase_stdout"
else
    "$PLUGIN_ROOT/scripts/larch-log.sh" append "${args[@]}" --record-file "$PAYLOAD_FILE" > "$log_phase_stdout"
fi
while IFS= read -r line || [[ -n "$line" ]]; do
    emit "$line"
done < "$log_phase_stdout"
