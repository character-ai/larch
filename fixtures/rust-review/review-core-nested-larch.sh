#!/bin/sh
set -eu

scenario=$(cat "$CLAUDE_PLUGIN_ROOT/scenario")
if [ "$scenario" = "env-controls" ]; then
  [ "${LARCH_REVIEWER_PRUNE:-}" = off ]
  [ "${LARCH_REVIEWER_STRAGGLER_MULTIPLE:-}" = 0 ]
  [ "${LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS:-}" = 11 ]
  [ "${LARCH_REVIEWER_STRAGGLER_MAX_SECONDS:-}" = 22 ]
  [ "${LARCH_UNIQUE_FINDER_BONUS:-}" = 0.25 ]
fi
domain=${1:-}
verb=${2:-}
shift 2 || true

value_after() {
  target=$1
  shift
  while [ "$#" -gt 0 ]; do
    if [ "$1" = "$target" ]; then
      printf '%s' "${2:-}"
      return
    fi
    shift
  done
}

review_tmp=$(value_after --review-tmpdir "$@")
output_dir=$(value_after --output-dir "$@")
findings=$(value_after --findings-file "$@")
oos=$(value_after --oos-file "$@")

case "$domain:$verb" in
  review:gather-context)
    if [ "$scenario" = "description-empty" ]; then
      printf 'MODE=description\nSCOPE_FILES_COUNT=0\n'
    else
      printf 'MODE=diff\nDIFF_FILE=%s/diff.patch\nFILE_LIST_FILE=%s/scope-files.txt\nCOMMIT_COUNT=1\n' "$output_dir" "$output_dir"
      if [ "$scenario" = "dispatch-bootstrap-failure" ]; then
        rm "$0"
      fi
    fi
    ;;
  review:dispatch-panel)
    mkdir -p "$review_tmp"
    if [ "$scenario" = "snapshot-failure" ]; then
      ln -s panel-manifest.ndjson "$review_tmp/oos-accepted-review.md"
    fi
    if [ "$scenario" = "dispatch-exit" ]; then
      exit 7
    elif [ "$scenario" = "static-dropped-slots" ]; then
      correctness="$review_tmp/codex-specialist-correctness-output.txt"
      edge_cases="$review_tmp/codex-specialist-edge-cases-output.txt"
      testing="$review_tmp/cursor-specialist-testing-output.txt"
      printf 'review output\n' >"$correctness"
      printf 'review output\n' >"$edge_cases"
      printf 'review output\n' >"$testing"
      printf '{"agent":"codex","output":"%s"}\n{"agent":"codex","output":"%s"}\n{"agent":"cursor","output":"%s"}\n' "$correctness" "$edge_cases" "$testing" >"$review_tmp/panel-manifest.ndjson"
      printf 'ignored\ndyn-specialist\tcodex\tstraggler-dropped\nedge-cases\tcodex\tstraggler-dropped\ntesting\tcursor\ttool-absent\ncorrectness\tcodex\treviewer-failed\n' >"$review_tmp/dropped-slots.tsv"
      printf 'PANEL_MODE=waterfall\nPANEL_SHAPE=hard\nPANEL_TIER=MODERATE\nPANEL_MANIFEST=%s/panel-manifest.ndjson\nEXTERNAL_OUTPUT_FILES=%s %s %s\nDROPPED_SLOTS_FILE=%s/dropped-slots.tsv\n' "$review_tmp" "$correctness" "$edge_cases" "$testing" "$review_tmp"
    elif [ "$scenario" != "static-coverage-failure" ]; then
      : >"$review_tmp/panel-manifest.ndjson"
      printf 'PANEL_MODE=waterfall\nPANEL_SHAPE=hard\nPANEL_TIER=MODERATE\nPANEL_MANIFEST=%s/panel-manifest.ndjson\n' "$review_tmp"
    else
      printf 'PANEL_MODE=waterfall\nPANEL_SHAPE=hard\nPANEL_TIER=MODERATE\n'
    fi
    if [ "$scenario" = "pruned-empty" ] || [ "$scenario" = "snapshot-failure" ]; then
      printf 'SCOUT_STATUS=na\nDYNAMIC_SLOTS=0\nSTATIC_SLOT_COUNT=0\nPANEL_PRUNED_EMPTY=true\nPRUNE_STATUS=pruned-empty\nSLOT_COUNT=1\nLAUNCHED_SLOTS=1\n'
    else
      printf 'SCOUT_STATUS=na\nDYNAMIC_SLOTS=0\nSTATIC_SLOT_COUNT=0\nPANEL_PRUNED_EMPTY=false\nSLOT_COUNT=1\nLAUNCHED_SLOTS=1\n'
    fi
    if [ "$scenario" = "collect-bootstrap-failure" ]; then
      rm "$0"
    fi
    ;;
  review:collect-findings)
    if [ "$scenario" = "threshold-no-output" ]; then
      printf 'FINDINGS_COUNT=1\n'
      exit 0
    fi
    if [ "$scenario" = "parseable-no-collector" ]; then
      printf '### FINDING_1: correctness: source: detail\n- **Reviewer(s)**: alpha\n- **Concern**: concrete\n' >"$findings"
      : >"$oos"
      printf 'FINDINGS_COUNT=0\n'
      exit 0
    fi
    if [ "$scenario" = "static-dropped-slots" ]; then
      correctness="$review_tmp/codex-specialist-correctness-output.txt"
      edge_cases="$review_tmp/codex-specialist-edge-cases-output.txt"
      testing="$review_tmp/cursor-specialist-testing-output.txt"
      printf 'REVIEWER_FILE=%s\nSTATUS=OK\n\nREVIEWER_FILE=%s\nSTATUS=NOT_SUBSTANTIVE\n\nREVIEWER_FILE=%s\nSTATUS=OK\n' "$correctness" "$edge_cases" "$testing" >"$(dirname "$findings")/collector-results.env"
      : >"$findings"
      : >"$oos"
      printf 'FINDINGS_COUNT=0\n'
      exit 0
    fi
    if [ "$scenario" = "proposer-map-failure" ]; then
      printf '### FINDING_1: correctness: source: detail\n- **Concern**: missing reviewer\n' >"$findings"
    else
      printf '### FINDING_1: correctness: source: detail\n- **Reviewer(s)**: alpha\n- **Concern**: concrete\n' >"$findings"
    fi
    : >"$oos"
    printf 'REVIEWER_FILE=none\nSTATUS=OK\n' >"$(dirname "$findings")/collector-results.env"
    printf 'FINDINGS_COUNT=1\n'
    ;;
  review:check-reviewer-failure-threshold)
    if [ "$scenario" = "corrupt-manifest" ]; then
      printf 'review check-reviewer-failure-threshold: --panel-manifest is unreadable or contains invalid JSON\n' >&2
      exit 1
    fi
    printf 'THRESHOLD_OK=true\nTHRESHOLD_REASON=\nNOT_SUBSTANTIVE_SLOTS=0\n'
    ;;
  review:prune-nit-findings)
    printf 'PRUNED_COUNT=0\nINSCOPE_REMAINING=1\nSTATUS=ok\n'
    if [ "$scenario" = "aggregate-bootstrap-failure" ]; then
      rm "$0"
    fi
    ;;
  review:aggregate-findings)
    if [ "$scenario" = "aggregate-zero" ]; then
      printf 'REASON=ok\nMERGED_COUNT=0\n'
    else
      printf 'REASON=ok\nMERGED_COUNT=1\n'
    fi
    ;;
  agent:dispatch-voters)
    mkdir -p "$review_tmp"
    for index in 1 2 3; do
      voter="$review_tmp/voter-$index.txt"
      printf 'vote\n' >"$voter"
      printf 'VOTER_%s_PATH=%s\nVOTER_%s_STATUS=complete\nVOTER_%s_TOOL=codex-voter-%s\n' "$index" "$voter" "$index" "$index" "$index"
    done
    if [ "$scenario" = "tally-bootstrap-failure" ]; then
      rm "$0"
    fi
    ;;
  review:tally-code-votes)
    if [ "$scenario" = "tally-failure" ]; then
      exit 7
    fi
    classification="$review_tmp/classification.tsv"
    printf 'FINDING_1\taccepted\n' >"$classification"
    if [ "$scenario" = "classification-write-failure" ]; then
      ln -s classification.tsv "$review_tmp/findings-classification-round-map.env"
    fi
    printf 'TALLY_STATUS=ok\nACCEPTED_COUNT=1\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\nOUT_OF_SCOPE_DRIFT_COUNT=0\nFINDINGS_CLASSIFICATION_TSV_FILE=%s\n' "$classification"
    ;;
  review:reviewer-prune)
    printf 'fixture prune warning\n' >&2
    exit 1
    ;;
  review:emit-tally|run-log:write-round|progress:note|timing:record-vendor-task)
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
