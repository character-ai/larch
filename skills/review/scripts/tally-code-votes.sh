#!/usr/bin/env bash
# tally-code-votes.sh — Tally /review code-review votes from a 3-judge panel.
# Renamed from tally-votes.sh and rewritten to source scripts/lib-vote-tally.sh
# and apply the 3-voter threshold rules per voting-protocol.md.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-vote-tally.sh
source "$PLUGIN_ROOT/scripts/lib-vote-tally.sh"

usage() {
    larch_err "Usage: tally-code-votes.sh --ballot-file FILE --voter-files FILE... --review-tmpdir DIR [--session-env-path FILE] [--scope-files FILE] [--plan-file FILE] [--cursor-available true|false] [--codex-available true|false] [--both-down true|false]"
}

BALLOT_FILE=""
VOTER_FILES=()
REVIEW_TMPDIR=""
SESSION_ENV_PATH=""
SCOPE_FILES=""
PLAN_FILE=""
CURSOR_AVAILABLE=""
CODEX_AVAILABLE=""
BOTH_DOWN="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ballot-file) BALLOT_FILE="${2:?--ballot-file requires a value}"; shift 2 ;;
        --voter-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do VOTER_FILES+=("$1"); shift; done ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?--review-tmpdir requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --scope-files) SCOPE_FILES="${2:?--scope-files requires a value}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --cursor-available) CURSOR_AVAILABLE="${2:?--cursor-available requires a value}"; shift 2 ;;
        --codex-available) CODEX_AVAILABLE="${2:?--codex-available requires a value}"; shift 2 ;;
        --both-down) BOTH_DOWN="${2:?--both-down requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "tally-code-votes.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$BALLOT_FILE" && -f "$BALLOT_FILE" ]] || { larch_err "tally-code-votes.sh: --ballot-file must name a file"; exit 2; }
[[ -n "$REVIEW_TMPDIR" ]] || { larch_err "tally-code-votes.sh: --review-tmpdir is required"; exit 2; }
mkdir -p "$REVIEW_TMPDIR"

ACCEPTED_FINDINGS_FILE="$REVIEW_TMPDIR/accepted-findings.md"
REJECTED_FINDINGS_FILE="$REVIEW_TMPDIR/rejected-findings.md"
OOS_ACCEPTED_FILE="$REVIEW_TMPDIR/oos-accepted-review.md"
OOS_FILE="$REVIEW_TMPDIR/oos.md"
VOTING_TALLY_FILE="$REVIEW_TMPDIR/voting-tally.md"
TALLY_ENV_FILE="$REVIEW_TMPDIR/review-tally.env"

: > "$ACCEPTED_FINDINGS_FILE"
: > "$REJECTED_FINDINGS_FILE"
: > "$OOS_ACCEPTED_FILE"
: > "$OOS_FILE"
: > "$TALLY_ENV_FILE"

# When nested under /implement, write accepted OOS to the parent tmpdir so
# Step 9a.1 finds it at $IMPLEMENT_TMPDIR/oos-accepted-review.md.
if [[ -n "$SESSION_ENV_PATH" ]]; then
    OOS_ACCEPTED_OUT="$(dirname "$SESSION_ENV_PATH")/oos-accepted-review.md"
else
    OOS_ACCEPTED_OUT="$OOS_ACCEPTED_FILE"
fi
[[ "$OOS_ACCEPTED_OUT" != "$OOS_ACCEPTED_FILE" ]] && : > "$OOS_ACCEPTED_OUT"

WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/larch-tally-code-votes.XXXXXX")
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

BLOCK_DIR="$WORKDIR/blocks"
split_ballot_to_blocks "$BALLOT_FILE" "$BLOCK_DIR"

shopt -s nullglob
block_files=("$BLOCK_DIR"/*.md)
shopt -u nullglob

ACCEPTED_COUNT=0
REJECTED_COUNT=0
EXONERATED_COUNT=0
NEUTRAL_COUNT=0
OOS_ACCEPTED_COUNT=0
OOS_REJECTED_COUNT=0
OUT_OF_SCOPE_DRIFT_COUNT=0

# scope_drift_check: returns 0 (drift detected, reclassify as OOS) or 1 (keep in-scope).
# Fires only when SCOPE_FILES is a non-empty readable file. Logic:
#   1. Extract path-looking tokens from the block's first (heading) line.
#   2. If no parseable paths found → keep in-scope (conservative).
#   3. If any parseable path appears in SCOPE_FILES or PLAN_FILE → keep in-scope.
#   4. Otherwise → scope drift, reclassify as OOS.
scope_drift_check() {
    local block="$1"
    [[ -n "$SCOPE_FILES" && -s "$SCOPE_FILES" ]] || return 1
    local heading
    heading=$(head -n1 "$block" | tr -d '`*_')
    # Extract file paths: tokens matching path/file.ext[:digits] patterns.
    local paths
    paths=$(printf '%s' "$heading" | grep -oE '[a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+:[0-9]+' | sed 's/:[0-9]*$//' || true)
    if [[ -z "$paths" ]]; then
        # Also try without line number
        paths=$(printf '%s' "$heading" | grep -oE '[a-zA-Z][a-zA-Z0-9_./-]+\.[a-zA-Z][a-zA-Z0-9]*' || true)
    fi
    [[ -n "$paths" ]] || return 1  # no parseable path → keep in-scope
    while IFS= read -r fpath; do
        [[ -n "$fpath" ]] || continue
        if grep -Fxq "$fpath" "$SCOPE_FILES" 2>/dev/null; then
            return 1  # file in diff → in-scope
        fi
        if [[ -n "$PLAN_FILE" && -f "$PLAN_FILE" ]] && grep -Fq "$fpath" "$PLAN_FILE" 2>/dev/null; then
            return 1  # file mentioned in plan → in-scope
        fi
    done <<< "$paths"
    return 0  # all paths outside diff and plan → scope drift
}

record_tally_outcome() {
    local id="$1" accepted="$2" outcome="$3"
    printf 'FINDING_%s_ACCEPTED=%s\n' "${id#FINDING_}" "$accepted" >> "$TALLY_ENV_FILE"
    printf 'FINDING_%s_OUTCOME=%s\n' "${id#FINDING_}" "$outcome" >> "$TALLY_ENV_FILE"
}

# Voter eligibility is the panel-level count of available voter files. The
# deprecated --both-down flag maps to the 0-judge main-agent path.
ELIGIBLE_VOTERS="${#VOTER_FILES[@]}"
VOTING_SKIPPED_WARNING=""
if [[ "$BOTH_DOWN" == "true" ]]; then
    ELIGIBLE_VOTERS=0
fi

if (( ELIGIBLE_VOTERS == 0 )); then
    VOTING_SKIPPED_WARNING="**⚠ Degraded code-review panel: 0 judges available. Panel tier: main-agent-required. Manual adjudication needed.**"
    printf '# Code Review Voting Tally\n\n' > "$VOTING_TALLY_FILE"
    printf '%s\n\n' "$VOTING_SKIPPED_WARNING" >> "$VOTING_TALLY_FILE"
    emit_kv TALLY_STATUS main-agent-vote-required
    emit_kv ACCEPTED_COUNT "$ACCEPTED_COUNT"
    emit_kv REJECTED_COUNT "$REJECTED_COUNT"
    emit_kv EXONERATED_COUNT "$EXONERATED_COUNT"
    emit_kv NEUTRAL_COUNT "$NEUTRAL_COUNT"
    emit_kv OOS_ACCEPTED_COUNT "$OOS_ACCEPTED_COUNT"
    emit_kv OOS_REJECTED_COUNT "$OOS_REJECTED_COUNT"
    emit_kv VOTING_TALLY_FILE "$VOTING_TALLY_FILE"
    emit_kv TALLY_FILE "$TALLY_ENV_FILE"
    emit_kv ACCEPTED_FINDINGS_FILE "$ACCEPTED_FINDINGS_FILE"
    emit_kv REJECTED_FINDINGS_FILE "$REJECTED_FINDINGS_FILE"
    emit_kv OOS_ACCEPTED_FILE "$OOS_ACCEPTED_OUT"
    emit_kv OOS_FILE "$OOS_FILE"
    emit_kv TALLY_OK true
    emit_kv VOTER_COUNT 0
    emit_kv VOTING_SKIPPED_WARNING "$VOTING_SKIPPED_WARNING"
    exit 0
fi

# Voting path: at least 1 judge available. Tally each block.
score_rows="$WORKDIR/score-rows.tsv"
: > "$score_rows"

{
    printf '# Code Review Voting Tally\n\n'
    if (( ELIGIBLE_VOTERS < 3 )); then
        tier_label="$(panel_tier "$ELIGIBLE_VOTERS")"
        printf '**⚠ Degraded code-review panel: %s judge(s) available. Panel tier: %s.**\n\n' "$ELIGIBLE_VOTERS" "$tier_label"
    fi
    printf '## Per-finding vote breakdown\n\n'
    printf '| Item | YES | NO | EXON | NEUT | Result |\n'
    printf '|---|---:|---:|---:|---:|---|\n'

    for block in "${block_files[@]+"${block_files[@]}"}"; do
        id=$(basename "$block" .md)
        yes=0; no=0; exonerate=0; neutral=0
        for voter_file in "${VOTER_FILES[@]}"; do
            vote=$(vote_for_id "$id" "$voter_file")
            case "$vote" in
                YES) yes=$((yes + 1)) ;;
                NO) no=$((no + 1)) ;;
                EXONERATE) exonerate=$((exonerate + 1)) ;;
                *) neutral=$((neutral + 1)) ;;
            esac
        done

        result=$(classify_result "$yes" "$no" "$exonerate" "$ELIGIBLE_VOTERS")
        case "$result" in
            accepted|rejected|exonerated|neutral) ;;
            *)
                larch_err "tally-code-votes.sh: unknown classify_result outcome for $id: $result"
                exit 2
                ;;
        esac
        printf '| %s | %s | %s | %s | %s | %s |\n' "$id" "$yes" "$no" "$exonerate" "$neutral" "$result"

        reviewer=$(reviewer_for_block "$block")

        # Code review uses a single FINDING_N namespace; OOS items are tagged
        # via [OUT_OF_SCOPE] in the title heading line.
        is_oos=false
        if head -n1 "$block" | grep -Fq '[OUT_OF_SCOPE]'; then
            is_oos=true
        fi
        # Scope-fit gate: reclassify in-scope findings whose locations are all
        # outside the diff and the plan as OUT_OF_SCOPE_DRIFT.
        if [[ "$is_oos" == "false" ]] && scope_drift_check "$block"; then
            is_oos=true
            OUT_OF_SCOPE_DRIFT_COUNT=$((OUT_OF_SCOPE_DRIFT_COUNT + 1))
        fi
        kind="finding"
        [[ "$is_oos" == "true" ]] && kind="oos"
        printf '%s\t%s\t%s\n' "$reviewer" "$kind" "$result" >> "$score_rows"

        security=false
        if is_security_block "$block" 2>/dev/null; then
            security=true
        fi

        if [[ "$kind" == "finding" ]]; then
            if [[ "$result" == "accepted" ]]; then
                cat "$block" >> "$ACCEPTED_FINDINGS_FILE"
                printf '\n' >> "$ACCEPTED_FINDINGS_FILE"
                ACCEPTED_COUNT=$((ACCEPTED_COUNT + 1))
                record_tally_outcome "$id" true accepted
            else
                case "$result" in
                    rejected)
                        {
                            printf '### [%s] %s\n\n' "$result" "$id"
                            cat "$block"
                            printf '\nVote tally: YES=%s NO=%s EXON=%s NEUTRAL=%s\n\n' "$yes" "$no" "$exonerate" "$neutral"
                        } >> "$REJECTED_FINDINGS_FILE"
                        REJECTED_COUNT=$((REJECTED_COUNT + 1))
                        ;;
                    exonerated)
                        EXONERATED_COUNT=$((EXONERATED_COUNT + 1))
                        ;;
                    neutral)
                        NEUTRAL_COUNT=$((NEUTRAL_COUNT + 1))
                        ;;
                esac
                record_tally_outcome "$id" false "$result"
            fi
        else
            # OOS item
            cat "$block" >> "$OOS_FILE"
            printf '\nVote tally: YES=%s NO=%s EXON=%s NEUTRAL=%s Result=%s\n\n' "$yes" "$no" "$exonerate" "$neutral" "$result" >> "$OOS_FILE"
            if [[ "$result" == "accepted" ]]; then
                if [[ "$security" == "true" ]]; then
                    # Security-tagged accepted OOS: held locally only, never filed publicly.
                    :
                else
                    cat "$block" >> "$OOS_ACCEPTED_FILE"
                    printf '\n' >> "$OOS_ACCEPTED_FILE"
                    if [[ "$OOS_ACCEPTED_OUT" != "$OOS_ACCEPTED_FILE" ]]; then
                        cat "$block" >> "$OOS_ACCEPTED_OUT"
                        printf '\n' >> "$OOS_ACCEPTED_OUT"
                    fi
                fi
                OOS_ACCEPTED_COUNT=$((OOS_ACCEPTED_COUNT + 1))
                record_tally_outcome "$id" true accepted
            else
                OOS_REJECTED_COUNT=$((OOS_REJECTED_COUNT + 1))
                record_tally_outcome "$id" false "$result"
            fi
        fi
    done

    printf '\n## Reviewer Competition Scoreboard\n\n'
    printf '| Reviewer | Proposed | Accepted | Neutral/Exon | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral/Exon | OOS-Rejected | Score |\n'
    printf '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
    awk -F '\t' '
      {
        reviewer=$1; kind=$2; result=$3
        seen[reviewer]=1
        if (kind == "finding") {
          proposed[reviewer]++
          if (result == "accepted") accepted[reviewer]++
          else if (result == "neutral" || result == "exonerated") neutral[reviewer]++
          else rejected[reviewer]++
        } else {
          oos_proposed[reviewer]++
          if (result == "accepted") oos_accepted[reviewer]++
          else if (result == "neutral" || result == "exonerated") oos_neutral[reviewer]++
          else oos_rejected[reviewer]++
        }
      }
      END {
        for (reviewer in seen) {
          score=accepted[reviewer]+0 + oos_accepted[reviewer]+0 - rejected[reviewer]+0 - oos_rejected[reviewer]+0
          printf "| %s | %d | %d | %d | %d | %d | %d | %d | %d | %d |\n",
            reviewer, proposed[reviewer]+0, accepted[reviewer]+0, neutral[reviewer]+0,
            rejected[reviewer]+0, oos_proposed[reviewer]+0, oos_accepted[reviewer]+0,
            oos_neutral[reviewer]+0, oos_rejected[reviewer]+0, score
        }
      }
    ' "$score_rows" | sort
} > "$VOTING_TALLY_FILE"

{
    printf 'ACCEPTED_COUNT=%s\n' "$ACCEPTED_COUNT"
    printf 'REJECTED_COUNT=%s\n' "$REJECTED_COUNT"
    printf 'EXONERATED_COUNT=%s\n' "$EXONERATED_COUNT"
    printf 'NEUTRAL_COUNT=%s\n' "$NEUTRAL_COUNT"
    printf 'OOS_ACCEPTED_COUNT=%s\n' "$OOS_ACCEPTED_COUNT"
    printf 'OOS_REJECTED_COUNT=%s\n' "$OOS_REJECTED_COUNT"
} >> "$TALLY_ENV_FILE"

: "$CURSOR_AVAILABLE" "$CODEX_AVAILABLE"

emit_kv TALLY_STATUS ok
emit_kv ACCEPTED_COUNT "$ACCEPTED_COUNT"
emit_kv REJECTED_COUNT "$REJECTED_COUNT"
emit_kv EXONERATED_COUNT "$EXONERATED_COUNT"
emit_kv NEUTRAL_COUNT "$NEUTRAL_COUNT"
emit_kv OOS_ACCEPTED_COUNT "$OOS_ACCEPTED_COUNT"
emit_kv OOS_REJECTED_COUNT "$OOS_REJECTED_COUNT"
emit_kv OUT_OF_SCOPE_DRIFT_COUNT "$OUT_OF_SCOPE_DRIFT_COUNT"
emit_kv VOTING_TALLY_FILE "$VOTING_TALLY_FILE"
emit_kv TALLY_FILE "$TALLY_ENV_FILE"
emit_kv ACCEPTED_FINDINGS_FILE "$ACCEPTED_FINDINGS_FILE"
emit_kv REJECTED_FINDINGS_FILE "$REJECTED_FINDINGS_FILE"
emit_kv OOS_ACCEPTED_FILE "$OOS_ACCEPTED_OUT"
emit_kv OOS_FILE "$OOS_FILE"
emit_kv TALLY_OK true
emit_kv VOTER_COUNT "$ELIGIBLE_VOTERS"
