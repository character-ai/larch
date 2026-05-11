#!/usr/bin/env bash
# write-run-params.sh - Atomically write run-depth router parameters.

set -euo pipefail

CLASSIFICATION=""
REASON=""
SOURCE=""
SKETCH_BUDGET=""
REVIEW_BUDGET=""
WORKFLOW_PATH=""
OUTPUT=""

usage() {
    cat >&2 <<'USAGE'
usage: write-run-params.sh --classification <TRIVIAL_DOC_ONLY|SIMPLE|HARD> --reason <text> --source <router-pre-design|caller-forwarded> --sketch-budget <0|2|4> --review-budget <quick|full> --workflow-path <SIMPLE|HARD> --output <path>
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
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "write-run-params.sh: unknown flag: $1" >&2
            usage
            exit 2
            ;;
    esac
done

require_present() {
    local name="$1"
    local value="$2"
    if [[ -z "$value" ]]; then
        echo "write-run-params.sh: missing required flag: $name" >&2
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
    echo "write-run-params.sh: invalid $name: $value" >&2
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
require_enum "--source" "$SOURCE" router-pre-design caller-forwarded
require_enum "--sketch-budget" "$SKETCH_BUDGET" 0 2 4
require_enum "--review-budget" "$REVIEW_BUDGET" quick full
require_enum "--workflow-path" "$WORKFLOW_PATH" SIMPLE HARD

case "$OUTPUT" in
    /*) ;;
    *)
        echo "write-run-params.sh: --output must be absolute: $OUTPUT" >&2
        exit 2
        ;;
esac

OUT_DIR=$(dirname "$OUTPUT")
if [[ ! -d "$OUT_DIR" ]]; then
    echo "write-run-params.sh: output directory not found: $OUT_DIR" >&2
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
    '{
      schema_version: 1,
      design_classification: $classification,
      design_classification_reason: $reason,
      design_classification_source: $source,
      sketch_budget: $sketch_budget,
      review_budget: $review_budget,
      workflow_path: $workflow_path
    }' > "$TMP"

mv "$TMP" "$OUTPUT"
trap - EXIT
printf 'RUN_PARAMS_WRITTEN=%s\n' "$OUTPUT"
