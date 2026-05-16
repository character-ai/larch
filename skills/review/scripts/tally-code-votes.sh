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
    larch_err "Usage: tally-code-votes.sh --ballot-file FILE --voter-files FILE... --review-tmpdir DIR [--session-env-path FILE] [--cursor-available true|false] [--codex-available true|false] [--both-down true|false]"
}

BALLOT_FILE=""
VOTER_FILES=()
REVIEW_TMPDIR=""
SESSION_ENV_PATH=""
CURSOR_AVAILABLE=""
CODEX_AVAILABLE=""
BOTH_DOWN="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ballot-file) BALLOT_FILE="${2:?--ballot-file requires a value}"; shift 2 ;;
        --voter-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do VOTER_FILES+=("$1"); shift; done ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?--review-tmpdir requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
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
OOS_ACCEPTED_COUNT=0
OOS_REJECTED_COUNT=0

# Voter eligibility: BOTH_DOWN=true skips voting entirely and accepts all.
# Otherwise count provided voter files.
ELIGIBLE_VOTERS="${#VOTER_FILES[@]}"
VOTING_SKIPPED_WARNING=""

if [[ "$BOTH_DOWN" == "true" ]]; then
    # Inherits the legacy fallback: when no review machinery is available,
    # accept all findings without voting.
    : > "$VOTING_TALLY_FILE"
    printf '# Code Review Voting Tally\n\n' >> "$VOTING_TALLY_FILE"
    printf '**Both external reviewers unavailable; voting skipped — all findings accepted.**\n\n' >> "$VOTING_TALLY_FILE"
    for block in "${block_files[@]+"${block_files[@]}"}"; do
        id=$(basename "$block" .md)
        # In /review code review all blocks live in the FINDING_N namespace;
        # OOS items are tagged via [OUT_OF_SCOPE] in the title line.
        is_oos=false
        if head -n1 "$block" | grep -Fq '[OUT_OF_SCOPE]'; then
            is_oos=true
        fi
        if [[ "$is_oos" == "true" ]]; then
            cat "$block" >> "$OOS_ACCEPTED_FILE"
            printf '\n' >> "$OOS_ACCEPTED_FILE"
            if [[ "$OOS_ACCEPTED_OUT" != "$OOS_ACCEPTED_FILE" ]]; then
                cat "$block" >> "$OOS_ACCEPTED_OUT"
                printf '\n' >> "$OOS_ACCEPTED_OUT"
            fi
            cat "$block" >> "$OOS_FILE"
            printf '\nVote tally: skipped (both-down)\n\n' >> "$OOS_FILE"
            OOS_ACCEPTED_COUNT=$((OOS_ACCEPTED_COUNT + 1))
        else
            cat "$block" >> "$ACCEPTED_FINDINGS_FILE"
            printf '\n' >> "$ACCEPTED_FINDINGS_FILE"
            ACCEPTED_COUNT=$((ACCEPTED_COUNT + 1))
        fi
        printf 'FINDING_%s_ACCEPTED=true\n' "${id#FINDING_}" >> "$TALLY_ENV_FILE"
    done
    emit_kv ACCEPTED_COUNT "$ACCEPTED_COUNT"
    emit_kv REJECTED_COUNT "$REJECTED_COUNT"
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
    emit_kv VOTING_SKIPPED_WARNING "**⚠ Voting skipped (both external reviewers down). All findings accepted.**"
    exit 0
fi

if (( ELIGIBLE_VOTERS < 2 )); then
    VOTING_SKIPPED_WARNING="**⚠ Voting skipped (${ELIGIBLE_VOTERS} judge(s) available, minimum 2 required). All findings accepted.**"
    : > "$VOTING_TALLY_FILE"
    printf '# Code Review Voting Tally\n\n' >> "$VOTING_TALLY_FILE"
    printf '**%s**\n\n' "$VOTING_SKIPPED_WARNING" >> "$VOTING_TALLY_FILE"
    for block in "${block_files[@]+"${block_files[@]}"}"; do
        id=$(basename "$block" .md)
        is_oos=false
        if head -n1 "$block" | grep -Fq '[OUT_OF_SCOPE]'; then
            is_oos=true
        fi
        if [[ "$is_oos" == "true" ]]; then
            cat "$block" >> "$OOS_ACCEPTED_FILE"; printf '\n' >> "$OOS_ACCEPTED_FILE"
            if [[ "$OOS_ACCEPTED_OUT" != "$OOS_ACCEPTED_FILE" ]]; then
                cat "$block" >> "$OOS_ACCEPTED_OUT"; printf '\n' >> "$OOS_ACCEPTED_OUT"
            fi
            cat "$block" >> "$OOS_FILE"
            printf '\nVote tally: skipped (insufficient voters)\n\n' >> "$OOS_FILE"
            OOS_ACCEPTED_COUNT=$((OOS_ACCEPTED_COUNT + 1))
        else
            cat "$block" >> "$ACCEPTED_FINDINGS_FILE"; printf '\n' >> "$ACCEPTED_FINDINGS_FILE"
            ACCEPTED_COUNT=$((ACCEPTED_COUNT + 1))
        fi
        printf 'FINDING_%s_ACCEPTED=true\n' "${id#FINDING_}" >> "$TALLY_ENV_FILE"
    done
    emit_kv ACCEPTED_COUNT "$ACCEPTED_COUNT"
    emit_kv REJECTED_COUNT "$REJECTED_COUNT"
    emit_kv OOS_ACCEPTED_COUNT "$OOS_ACCEPTED_COUNT"
    emit_kv OOS_REJECTED_COUNT "$OOS_REJECTED_COUNT"
    emit_kv VOTING_TALLY_FILE "$VOTING_TALLY_FILE"
    emit_kv TALLY_FILE "$TALLY_ENV_FILE"
    emit_kv ACCEPTED_FINDINGS_FILE "$ACCEPTED_FINDINGS_FILE"
    emit_kv REJECTED_FINDINGS_FILE "$REJECTED_FINDINGS_FILE"
    emit_kv OOS_ACCEPTED_FILE "$OOS_ACCEPTED_OUT"
    emit_kv OOS_FILE "$OOS_FILE"
    emit_kv TALLY_OK true
    emit_kv VOTER_COUNT "$ELIGIBLE_VOTERS"
    emit_kv VOTING_SKIPPED_WARNING "$VOTING_SKIPPED_WARNING"
    exit 0
fi

# Voting path: at least 2 judges available. Tally each block.
score_rows="$WORKDIR/score-rows.tsv"
: > "$score_rows"

{
    printf '# Code Review Voting Tally\n\n'
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

        effective_eligible=$(( yes + no + exonerate ))
        use_eligible="$ELIGIBLE_VOTERS"
        (( effective_eligible < use_eligible )) && use_eligible="$effective_eligible"

        result=$(classify_result "$yes" "$no" "$exonerate" "$use_eligible")
        printf '| %s | %s | %s | %s | %s | %s |\n' "$id" "$yes" "$no" "$exonerate" "$neutral" "$result"

        reviewer=$(reviewer_for_block "$block")

        # Code review uses a single FINDING_N namespace; OOS items are tagged
        # via [OUT_OF_SCOPE] in the title heading line.
        is_oos=false
        if head -n1 "$block" | grep -Fq '[OUT_OF_SCOPE]'; then
            is_oos=true
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
                printf 'FINDING_%s_ACCEPTED=true\n' "${id#FINDING_}" >> "$TALLY_ENV_FILE"
            else
                {
                    printf '### [%s] %s\n\n' "$result" "$id"
                    cat "$block"
                    printf '\nVote tally: YES=%s NO=%s EXON=%s NEUTRAL=%s\n\n' "$yes" "$no" "$exonerate" "$neutral"
                } >> "$REJECTED_FINDINGS_FILE"
                REJECTED_COUNT=$((REJECTED_COUNT + 1))
                printf 'FINDING_%s_ACCEPTED=false\n' "${id#FINDING_}" >> "$TALLY_ENV_FILE"
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
                printf 'FINDING_%s_ACCEPTED=true\n' "${id#FINDING_}" >> "$TALLY_ENV_FILE"
            else
                OOS_REJECTED_COUNT=$((OOS_REJECTED_COUNT + 1))
                printf 'FINDING_%s_ACCEPTED=false\n' "${id#FINDING_}" >> "$TALLY_ENV_FILE"
            fi
        fi
    done

    printf '\n## Reviewer Competition Scoreboard\n\n'
    printf '| Reviewer | Proposed | Accepted | Neutral/Exon | Rejected | OOS-Proposed | OOS-Accepted | Score |\n'
    printf '|---|---:|---:|---:|---:|---:|---:|---:|\n'
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
        }
      }
      END {
        for (reviewer in seen) {
          score=accepted[reviewer]+0 + oos_accepted[reviewer]+0 - rejected[reviewer]+0
          printf "| %s | %d | %d | %d | %d | %d | %d | %d |\n",
            reviewer, proposed[reviewer]+0, accepted[reviewer]+0, neutral[reviewer]+0,
            rejected[reviewer]+0, oos_proposed[reviewer]+0, oos_accepted[reviewer]+0, score
        }
      }
    ' "$score_rows" | sort
} > "$VOTING_TALLY_FILE"

: "$CURSOR_AVAILABLE" "$CODEX_AVAILABLE"

emit_kv ACCEPTED_COUNT "$ACCEPTED_COUNT"
emit_kv REJECTED_COUNT "$REJECTED_COUNT"
emit_kv OOS_ACCEPTED_COUNT "$OOS_ACCEPTED_COUNT"
emit_kv OOS_REJECTED_COUNT "$OOS_REJECTED_COUNT"
emit_kv VOTING_TALLY_FILE "$VOTING_TALLY_FILE"
emit_kv TALLY_FILE "$TALLY_ENV_FILE"
emit_kv ACCEPTED_FINDINGS_FILE "$ACCEPTED_FINDINGS_FILE"
emit_kv REJECTED_FINDINGS_FILE "$REJECTED_FINDINGS_FILE"
emit_kv OOS_ACCEPTED_FILE "$OOS_ACCEPTED_OUT"
emit_kv OOS_FILE "$OOS_FILE"
emit_kv TALLY_OK true
emit_kv VOTER_COUNT "$ELIGIBLE_VOTERS"
