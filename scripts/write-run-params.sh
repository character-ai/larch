#!/usr/bin/env bash
# write-run-params.sh - Atomically write run-depth router parameters.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

CLASSIFICATION=""
REASON=""
SOURCE=""
SKETCH_BUDGET=""
REVIEW_BUDGET=""
WORKFLOW_PATH=""
OUTPUT=""
PARTITION_REQUESTED=""

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
usage: write-run-params.sh --classification <TRIVIAL_DOC_ONLY|SIMPLE|HARD> --reason <text> --source <caller-forwarded> --sketch-budget <0|2|4> --review-budget <quick|full> --workflow-path <SIMPLE|HARD> --output <path> [--partition-requested <true|false>]
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --classification)
            CLASSIFICATION="${2:?--classification requires a value}"
            shift 2
            ;;
        --reason)
            REASON="${2:?--reason requires a value}"
            shift 2
            ;;
        --source)
            SOURCE="${2:?--source requires a value}"
            shift 2
            ;;
        --sketch-budget)
            SKETCH_BUDGET="${2:?--sketch-budget requires a value}"
            shift 2
            ;;
        --review-budget)
            REVIEW_BUDGET="${2:?--review-budget requires a value}"
            shift 2
            ;;
        --workflow-path)
            WORKFLOW_PATH="${2:?--workflow-path requires a value}"
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
require_present "--reason" "$REASON"
require_present "--source" "$SOURCE"
require_present "--sketch-budget" "$SKETCH_BUDGET"
require_present "--review-budget" "$REVIEW_BUDGET"
require_present "--workflow-path" "$WORKFLOW_PATH"
require_present "--output" "$OUTPUT"

require_enum "--classification" "$CLASSIFICATION" TRIVIAL_DOC_ONLY SIMPLE HARD
require_enum "--source" "$SOURCE" caller-forwarded
require_enum "--sketch-budget" "$SKETCH_BUDGET" 0 2 4
require_enum "--review-budget" "$REVIEW_BUDGET" quick full
require_enum "--workflow-path" "$WORKFLOW_PATH" SIMPLE HARD

if [[ -n "$PARTITION_REQUESTED" ]]; then
    require_enum "--partition-requested" "$PARTITION_REQUESTED" true false
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
    --arg reason "$REASON" \
    --arg source "$SOURCE" \
    --argjson sketch_budget "$SKETCH_BUDGET" \
    --arg review_budget "$REVIEW_BUDGET" \
    --arg workflow_path "$WORKFLOW_PATH" \
    --arg partition_requested "${PARTITION_REQUESTED:-false}" \
    '{
      schema_version: 1,
      design_classification: $classification,
      design_classification_reason: $reason,
      design_classification_source: $source,
      sketch_budget: $sketch_budget,
      review_budget: $review_budget,
      workflow_path: $workflow_path,
      partition_requested: ($partition_requested == "true")
    }' > "$TMP"

mv "$TMP" "$OUTPUT"
trap - EXIT
emit_kv RUN_PARAMS_WRITTEN "$OUTPUT"
