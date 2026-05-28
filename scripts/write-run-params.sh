#!/usr/bin/env bash
# write-run-params.sh - Atomically write /design router parameters.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

CLASSIFICATION=""
OUTPUT=""
REASON=""
SOURCE=""
SKETCH_BUDGET=""
REVIEW_BUDGET=""
WORKFLOW_PATH=""
PARTITION_REQUESTED=""
BRAINSTORM_REQUESTED=""
MANUAL_GATE_B=""

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
usage: write-run-params.sh --classification <SIMPLE|HARD> --output <path> [--reason <text>] [--source <text>] [--sketch-budget <0|2|4>] [--review-budget <quick|full>] [--workflow-path <SIMPLE|HARD>] [--partition-requested <true|false>] [--brainstorm-requested <true|false>] [--manual-gate-b <true|false>]
USAGE
}

take_value() {
    local flag="$1"
    if [[ $# -lt 2 ]]; then
        larch_err "write-run-params.sh: $flag requires a value"
        exit 2
    fi
    printf '%s' "$2"
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
        --reason)
            if [[ $# -lt 2 ]]; then
                larch_err "write-run-params.sh: --reason requires a value"
                exit 2
            fi
            REASON="$(take_value --reason "$2")"
            shift 2
            ;;
        --source)
            if [[ $# -lt 2 ]]; then
                larch_err "write-run-params.sh: --source requires a value"
                exit 2
            fi
            SOURCE="$(take_value --source "$2")"
            shift 2
            ;;
        --sketch-budget)
            if [[ $# -lt 2 ]]; then
                larch_err "write-run-params.sh: --sketch-budget requires a value"
                exit 2
            fi
            SKETCH_BUDGET="$(take_value --sketch-budget "$2")"
            shift 2
            ;;
        --review-budget)
            if [[ $# -lt 2 ]]; then
                larch_err "write-run-params.sh: --review-budget requires a value"
                exit 2
            fi
            REVIEW_BUDGET="$(take_value --review-budget "$2")"
            shift 2
            ;;
        --workflow-path)
            if [[ $# -lt 2 ]]; then
                larch_err "write-run-params.sh: --workflow-path requires a value"
                exit 2
            fi
            WORKFLOW_PATH="$(take_value --workflow-path "$2")"
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
            if [[ $# -lt 2 || -z "${2-}" ]]; then
                larch_err "write-run-params.sh: --manual-gate-b requires a value"
                exit 2
            fi
            MANUAL_GATE_B="$2"
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

if [[ -n "$SKETCH_BUDGET" ]]; then
    require_enum "--sketch-budget" "$SKETCH_BUDGET" 0 2 4
fi

if [[ -n "$REVIEW_BUDGET" ]]; then
    require_enum "--review-budget" "$REVIEW_BUDGET" quick full
fi

if [[ -n "$WORKFLOW_PATH" ]]; then
    require_enum "--workflow-path" "$WORKFLOW_PATH" SIMPLE HARD
fi

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
    --arg reason "${REASON:-}" \
    --arg source "${SOURCE:-}" \
    --arg sketch_budget "${SKETCH_BUDGET:-}" \
    --arg review_budget "${REVIEW_BUDGET:-}" \
    --arg workflow_path "${WORKFLOW_PATH:-}" \
    --arg partition_requested "${PARTITION_REQUESTED:-false}" \
    --arg brainstorm_requested "${BRAINSTORM_REQUESTED:-false}" \
    --arg manual_gate_b "${MANUAL_GATE_B:-false}" \
    '{
      schema_version: 3,
      design_classification: $classification,
      design_classification_reason: (if $reason == "" then null else $reason end),
      design_classification_source: (if $source == "" then null else $source end),
      sketch_budget: (if $sketch_budget == "" then null else ($sketch_budget | tonumber) end),
      review_budget: (if $review_budget == "" then null else $review_budget end),
      workflow_path: (if $workflow_path == "" then null else $workflow_path end),
      partition_requested: ($partition_requested == "true"),
      brainstorm_requested: ($brainstorm_requested == "true"),
      manual_gate_b: ($manual_gate_b == "true")
    }' > "$TMP"

mv "$TMP" "$OUTPUT"
trap - EXIT
emit_kv RUN_PARAMS_WRITTEN "$OUTPUT"
