#!/usr/bin/env bash
# write-run-params.sh - Atomically write /design router parameters.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

CLASSIFICATION=""
OUTPUT=""
PARTITION_REQUESTED=""
BRAINSTORM_REQUESTED=""
MANUAL_GATE_B=""

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
usage: write-run-params.sh --classification <SIMPLE|HARD> --output <path> [--partition-requested <true|false>] [--brainstorm-requested <true|false>] [--manual-gate-b <true|false>]
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --classification)
            CLASSIFICATION="${2:?--classification requires a value}"
            shift 2
            ;;
        --output)
            OUTPUT="${2:?--output requires a value}"
            shift 2
            ;;
        --partition-requested)
            PARTITION_REQUESTED="${2:?--partition-requested requires a value}"
            shift 2
            ;;
        --brainstorm-requested)
            BRAINSTORM_REQUESTED="${2:?--brainstorm-requested requires a value}"
            shift 2
            ;;
        --manual-gate-b)
            MANUAL_GATE_B="${2:?--manual-gate-b requires a value}"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            larch_err "write-run-params.sh: unknown flag: $1"
            usage
            exit 2
            ;;
    esac
done

require_present() {
    local name="$1"
    local value="$2"
    if [[ -z "$value" ]]; then
        larch_err "write-run-params.sh: missing required flag: $name"
        usage
        exit 2
    fi
}

require_enum() {
    local name="$1"
    local value="$2"
    shift 2
    local allowed
    for allowed in "$@"; do
        [[ "$value" == "$allowed" ]] && return 0
    done
    larch_err "write-run-params.sh: invalid $name: $value"
    exit 2
}

require_present "--classification" "$CLASSIFICATION"
require_present "--output" "$OUTPUT"

require_enum "--classification" "$CLASSIFICATION" SIMPLE HARD

if [[ -n "$PARTITION_REQUESTED" ]]; then
    require_enum "--partition-requested" "$PARTITION_REQUESTED" true false
fi

if [[ -n "$BRAINSTORM_REQUESTED" ]]; then
    require_enum "--brainstorm-requested" "$BRAINSTORM_REQUESTED" true false
fi

if [[ -n "$MANUAL_GATE_B" ]]; then
    require_enum "--manual-gate-b" "$MANUAL_GATE_B" true false
fi

case "$OUTPUT" in
    /*) ;;
    *)
        larch_err "write-run-params.sh: --output must be absolute: $OUTPUT"
        exit 2
        ;;
esac

OUT_DIR=$(dirname "$OUTPUT")
if [[ ! -d "$OUT_DIR" ]]; then
    larch_err "write-run-params.sh: output directory not found: $OUT_DIR"
    exit 1
fi

TMP=$(mktemp "${OUTPUT}.tmp.XXXXXX")
cleanup() {
    rm -f "$TMP"
}
trap cleanup EXIT

jq -n \
    --arg classification "$CLASSIFICATION" \
    --arg partition_requested "${PARTITION_REQUESTED:-false}" \
    --arg brainstorm_requested "${BRAINSTORM_REQUESTED:-false}" \
    --arg manual_gate_b "${MANUAL_GATE_B:-false}" \
    '{
      schema_version: 2,
      design_classification: $classification,
      partition_requested: ($partition_requested == "true"),
      brainstorm_requested: ($brainstorm_requested == "true"),
      manual_gate_b: ($manual_gate_b == "true")
    }' > "$TMP"

mv "$TMP" "$OUTPUT"
trap - EXIT
emit_kv RUN_PARAMS_WRITTEN "$OUTPUT"
