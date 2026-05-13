#!/usr/bin/env bash
# emit-tally.sh — Emit review round summaries and structured review summary.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SHARED_DIR="$SCRIPT_DIR/../../shared/scripts"

usage() { echo "Usage: emit-tally.sh --tally-file FILE --accepted-findings-file FILE --oos-file FILE --review-tmpdir DIR --round N --mode diff|description [--session-env-path FILE] [--implement-tmpdir DIR]" >&2; }

TALLY_FILE=""
ACCEPTED_FINDINGS_FILE=""
OOS_FILE=""
REVIEW_TMPDIR=""
SESSION_ENV_PATH=""
ROUND="1"
MODE=""
IMPLEMENT_TMPDIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tally-file) TALLY_FILE="${2:?--tally-file requires a value}"; shift 2 ;;
        --accepted-findings-file) ACCEPTED_FINDINGS_FILE="${2:?--accepted-findings-file requires a value}"; shift 2 ;;
        --oos-file) OOS_FILE="${2:?--oos-file requires a value}"; shift 2 ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?--review-tmpdir requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --round) ROUND="${2:?--round requires a value}"; shift 2 ;;
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --implement-tmpdir) IMPLEMENT_TMPDIR="${2:?--implement-tmpdir requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "emit-tally.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

[[ -n "$REVIEW_TMPDIR" ]] || { echo "emit-tally.sh: --review-tmpdir is required" >&2; exit 2; }
[[ -n "$TALLY_FILE" && -f "$TALLY_FILE" ]] || { echo "emit-tally.sh: --tally-file must name a file" >&2; exit 2; }
[[ -n "$ACCEPTED_FINDINGS_FILE" && -f "$ACCEPTED_FINDINGS_FILE" ]] || { echo "emit-tally.sh: --accepted-findings-file must name a file" >&2; exit 2; }
mkdir -p "$REVIEW_TMPDIR"

ROUND_SUMMARY_FILE="$REVIEW_TMPDIR/review-round-summary.md"
REVIEW_SUMMARY_FILE="$REVIEW_TMPDIR/review-summary.json"
REJECTED_FINDINGS_FILE="$REVIEW_TMPDIR/rejected-findings.md"
OOS_ACCEPTED_FILE="$REVIEW_TMPDIR/oos-accepted-review.md"

accepted=$(grep -c 'ACCEPTED=true' "$TALLY_FILE" || true)
rejected=$(grep -c 'ACCEPTED=false' "$TALLY_FILE" || true)

{
    printf '# Review Round %s\n\n' "$ROUND"
    printf '%s\n' "- Mode: \`$MODE\`"
    printf '%s\n' "- Accepted findings: $accepted"
    printf '%s\n\n' "- Rejected findings: $rejected"
    if [[ -s "$ACCEPTED_FINDINGS_FILE" ]]; then
        printf '## Accepted Findings\n\n'
        cat "$ACCEPTED_FINDINGS_FILE"
    fi
} > "$ROUND_SUMMARY_FILE"

{
    printf '# Rejected Findings\n\n'
    grep -n 'ACCEPTED=false' "$TALLY_FILE" || true
} > "$REJECTED_FINDINGS_FILE"

# Collect reviewer output paths from the review tmpdir for the JSON schema.
reviewer_paths=()
while IFS= read -r f; do
    reviewer_paths+=("$f")
done < <(find "$REVIEW_TMPDIR" -maxdepth 1 -name '*-output.txt' 2>/dev/null | sort)
reviewer_paths_json=$(printf '%s\n' "${reviewer_paths[@]+"${reviewer_paths[@]}"}" | jq -R . | jq -s .)

# Emit schema matching heavy-worker.md contract: schema_version, rounds_completed,
# reviewer_output_paths, finding_counts.{total_accepted,total_rejected}, accepted_count, rejected_count.
jq -n \
    --argjson round "$ROUND" \
    --argjson accepted "$accepted" \
    --argjson rejected "$rejected" \
    --argjson paths "$reviewer_paths_json" \
    '{
        schema_version: 1,
        rounds_completed: $round,
        reviewer_output_paths: $paths,
        finding_counts: { total_accepted: $accepted, total_rejected: $rejected },
        accepted_count: $accepted,
        rejected_count: $rejected
    }' \
    > "$REVIEW_SUMMARY_FILE"

if [[ -n "$OOS_FILE" && -f "$OOS_FILE" ]]; then
    oos_args=(--findings-file "$OOS_FILE" --output-file "$OOS_ACCEPTED_FILE")
    [[ -n "$SESSION_ENV_PATH" ]] && oos_args+=(--session-env-path "$SESSION_ENV_PATH")
    "$SHARED_DIR/oos-serialize.sh" "${oos_args[@]}" >/dev/null || true
else
    : > "$OOS_ACCEPTED_FILE"
fi

if [[ -n "$SESSION_ENV_PATH" ]]; then
    parent_dir=$(dirname "$SESSION_ENV_PATH")
    cp "$ROUND_SUMMARY_FILE" "$parent_dir/review-round-summary.md" 2>/dev/null || true
    cp "$REVIEW_SUMMARY_FILE" "$parent_dir/review-summary.json" 2>/dev/null || true
fi
if [[ -n "$IMPLEMENT_TMPDIR" && -d "$IMPLEMENT_TMPDIR" ]]; then
    cp "$ROUND_SUMMARY_FILE" "$IMPLEMENT_TMPDIR/review-round-summary.md" 2>/dev/null || true
    cp "$REVIEW_SUMMARY_FILE" "$IMPLEMENT_TMPDIR/review-summary.json" 2>/dev/null || true
fi

printf 'EMIT_OK=true\n'
printf 'ROUND_SUMMARY_FILE=%q\n' "$ROUND_SUMMARY_FILE"
printf 'REVIEW_SUMMARY_FILE=%q\n' "$REVIEW_SUMMARY_FILE"
