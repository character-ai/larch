#!/usr/bin/env bash
# tally-code-votes.sh — Tally /review code-review votes from a round-aware panel.
# Renamed from tally-votes.sh and rewritten to source scripts/lib-vote-tally.sh
# and apply the active threshold rules per voting-protocol.md.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-vote-tally.sh
source "$PLUGIN_ROOT/scripts/lib-vote-tally.sh"
# shellcheck source=scripts/lib-voter-parse-rate.sh
source "$PLUGIN_ROOT/scripts/lib-voter-parse-rate.sh"

usage() {
    larch_err "Usage: tally-code-votes.sh --ballot-file FILE --voter-files FILE... --review-tmpdir DIR [--session-env-path FILE] [--scope-files FILE] [--plan-file FILE] [--manifest-file FILE] [--collector-results-file FILE] [--not-substantive-count N] [--cursor-available true|false] [--codex-available true|false] [--round-num N] [--both-down true|false]"
}

BALLOT_FILE=""
VOTER_FILES=()
REVIEW_TMPDIR=""
SESSION_ENV_PATH=""
SCOPE_FILES=""
PLAN_FILE=""
MANIFEST_FILE=""
COLLECTOR_RESULTS_FILE=""
NOT_SUBSTANTIVE_COUNT=0
CURSOR_AVAILABLE=""
CODEX_AVAILABLE=""
ROUND_NUM=1
BOTH_DOWN="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ballot-file) BALLOT_FILE="${2:?--ballot-file requires a value}"; shift 2 ;;
        --voter-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do VOTER_FILES+=("$1"); shift; done ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?--review-tmpdir requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --scope-files) SCOPE_FILES="${2:?--scope-files requires a value}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --manifest-file) MANIFEST_FILE="${2:?--manifest-file requires a value}"; shift 2 ;;
        --collector-results-file) COLLECTOR_RESULTS_FILE="${2:?--collector-results-file requires a value}"; shift 2 ;;
        --not-substantive-count) NOT_SUBSTANTIVE_COUNT="${2:?--not-substantive-count requires a value}"; shift 2 ;;
        --cursor-available) CURSOR_AVAILABLE="${2:?--cursor-available requires a value}"; shift 2 ;;
        --codex-available) CODEX_AVAILABLE="${2:?--codex-available requires a value}"; shift 2 ;;
        --round-num) ROUND_NUM="${2:?--round-num requires a value}"; shift 2 ;;
        --both-down) BOTH_DOWN="${2:?--both-down requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "tally-code-votes.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$BALLOT_FILE" && -f "$BALLOT_FILE" ]] || { larch_err "tally-code-votes.sh: --ballot-file must name a file"; exit 2; }
[[ -n "$REVIEW_TMPDIR" ]] || { larch_err "tally-code-votes.sh: --review-tmpdir is required"; exit 2; }
[[ -z "$MANIFEST_FILE" || -f "$MANIFEST_FILE" ]] || { larch_err "tally-code-votes.sh: --manifest-file must name a file"; exit 2; }
case "$ROUND_NUM" in ''|*[!0-9]*) larch_err "tally-code-votes.sh: --round-num must be a positive integer"; exit 2 ;; esac
(( ROUND_NUM > 0 )) || { larch_err "tally-code-votes.sh: --round-num must be a positive integer"; exit 2; }
mkdir -p "$REVIEW_TMPDIR"

ACCEPTED_FINDINGS_FILE="$REVIEW_TMPDIR/accepted-findings.md"
REJECTED_FINDINGS_FILE="$REVIEW_TMPDIR/rejected-findings.md"
OOS_ACCEPTED_FILE="$REVIEW_TMPDIR/oos-accepted-review.md"
OOS_FILE="$REVIEW_TMPDIR/oos.md"
VOTING_TALLY_FILE="$REVIEW_TMPDIR/voting-tally.md"
TALLY_ENV_FILE="$REVIEW_TMPDIR/review-tally.env"
YIELD_TSV_FILE="$REVIEW_TMPDIR/scout-archetype-yield.tsv"
if [[ -n "$SESSION_ENV_PATH" || -n "${IMPLEMENT_TMPDIR:-}" ]]; then
    CLASSIFICATION_TSV="$REVIEW_TMPDIR/findings-classification.tsv"
else
    CLASSIFICATION_TSV="$REVIEW_TMPDIR/findings-classification-round-${ROUND_NUM}.tsv"
fi

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
if ! split_ballot_to_blocks "$BALLOT_FILE" "$BLOCK_DIR"; then
    larch_err "tally-code-votes.sh: duplicate or malformed FINDING/OOS headings in ballot"
    exit 2
fi

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

write_classification_tsv_header() {
    printf '%s\n' 'finding_id	reviewer_slots	voting_result	v1_vote	v1_correctness	v1_severity	v1_quality	v1_uncertain	v2_vote	v2_correctness	v2_severity	v2_quality	v2_uncertain	v3_vote	v3_correctness	v3_severity	v3_quality	v3_uncertain'
}

sanitize_classification_text_cell() {
    printf '%s' "${1:-}" | tr '\011\015\012' '   ' | sed 's/[[:space:]]*|[[:space:]]*/|/g'
}

reviewer_slots_for_tsv() {
    printf '%s\n' "${1:-}" | awk -F',' '
      {
        out = ""
        for (i = 1; i <= NF; i++) {
          gsub(/[\t\r\n]/, " ", $i)
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", $i)
          if ($i != "") out = (out == "" ? $i : out "|" $i)
        }
        print out
      }'
}

kv_value() {
    local key="$1"
    awk -F= -v k="$key" '$1 == k { print substr($0, length(k) + 2); found=1 } END { if (!found) print "" }'
}

sanitize_vote_cell() {
    case "${1:-}" in
        YES|NO|EXONERATE|JUDGE_ERROR) printf '%s' "$1" ;;
        *) printf '' ;;
    esac
}

sanitize_correctness_cell() {
    case "${1:-}" in
        true|partially-true|false-positive|uncertain) printf '%s' "$1" ;;
        *) printf '' ;;
    esac
}

sanitize_severity_cell() {
    case "${1:-}" in
        blocker|major|minor|nit|uncertain) printf '%s' "$1" ;;
        *) printf '' ;;
    esac
}

sanitize_quality_cell() {
    case "${1:-}" in
        excellent|good|adequate|weak|no-fix|uncertain) printf '%s' "$1" ;;
        *) printf '' ;;
    esac
}

sanitize_uncertain_cell() {
    case "${1:-}" in
        true|false) printf '%s' "$1" ;;
        *) printf 'true' ;;
    esac
}

sanitize_result_cell() {
    case "${1:-}" in
        accepted|rejected|exonerated|neutral) printf '%s' "$1" ;;
        *) printf '' ;;
    esac
}

parse_vote_rating_for() {
    local voter_file="$1" ballot_id="$2" parsed rc
    set +e
    parsed=$("$PLUGIN_ROOT/scripts/parse-judge-vote-and-rating.sh" "$voter_file" "$ballot_id" 2>/dev/null)
    rc=$?
    set -e
    if [[ "$rc" -ne 0 ]]; then
        emit_kv WARN "judge vote/rating parser failed for $(basename "$voter_file") $ballot_id (rc=$rc); treating vote as JUDGE_ERROR"
        printf 'PARSED_VOTE=JUDGE_ERROR\n'
        printf 'PARSED_CORRECTNESS=\n'
        printf 'PARSED_SEVERITY=\n'
        printf 'PARSED_QUALITY=\n'
        printf 'PARSED_UNCERTAIN=true\n'
    else
        printf '%s\n' "$parsed"
    fi
}

write_classification_tsv_row() {
    local ballot_id="$1" reviewer_slots="$2" voting_result="$3"
    shift 3
    local row=("$ballot_id" "$(sanitize_classification_text_cell "$(reviewer_slots_for_tsv "$reviewer_slots")")" "$(sanitize_result_cell "$voting_result")")
    local value vote correctness severity quality uncertain
    for _ in 1 2 3; do
        if [[ $# -lt 5 ]]; then
            row+=("" "" "" "" "")
            continue
        fi
        vote="${1:-}"; correctness="${2:-}"; severity="${3:-}"; quality="${4:-}"; uncertain="${5:-}"
        shift 5
        value=$(sanitize_vote_cell "$vote"); row+=("$value")
        value=$(sanitize_correctness_cell "$correctness")
        [[ -z "$value" ]] && uncertain=true
        row+=("$value")
        value=$(sanitize_severity_cell "$severity")
        [[ -z "$value" ]] && uncertain=true
        row+=("$value")
        value=$(sanitize_quality_cell "$quality")
        [[ -z "$value" ]] && uncertain=true
        row+=("$value")
        row+=("$(sanitize_uncertain_cell "$uncertain")")
    done
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "${row[@]}" >> "$CLASSIFICATION_TSV"
}

mkdir -p "$(dirname "$CLASSIFICATION_TSV")"
write_classification_tsv_header > "$CLASSIFICATION_TSV"

normalize_reviewer_basename() {
    local base="$1" stem ext=""
    base="${base##*/}"
    case "$base" in
        *.txt) stem="${base%.txt}"; ext=".txt" ;;
        *) stem="$base" ;;
    esac
    while :; do
        case "$stem" in
            *-phase2) stem="${stem%-phase2}" ;;
            *-phase3) stem="${stem%-phase3}" ;;
            *-retry) stem="${stem%-retry}" ;;
            *) break ;;
        esac
    done
    printf '%s%s' "$stem" "$ext"
}

expected_voters_for_round() {
    # Code review always targets a 3-judge panel; per-round `--round-num` does not shrink quorum.
    printf '3\n'
}

static_focus_area() {
    case "$1" in
        structure) printf 'code-quality' ;;
        correctness) printf 'correctness' ;;
        testing) printf 'risk-integration' ;;
        security) printf 'security' ;;
        edge-cases) printf 'correctness' ;;
        plan-fidelity) printf 'architecture' ;;
        *) printf 'code-quality' ;;
    esac
}

write_archetype_map() {
    local manifest_file="$1" map_file="$2" row base slot focus weight archetype static_slug
    : > "$map_file"
    [[ -n "$manifest_file" && -f "$manifest_file" ]] || return 0
    while IFS= read -r row || [[ -n "$row" ]]; do
        [[ -n "$row" ]] || continue
        base=$(printf '%s' "$row" | jq -r '.output | split("/")[-1]')
        slot=$(printf '%s' "$row" | jq -r '.slot // ""')
        focus=$(printf '%s' "$row" | jq -r '.focus_area // ""')
        weight=$(printf '%s' "$row" | jq -r '.weight // 1')
        base=$(normalize_reviewer_basename "$base")
        case "$base" in
            codex-generalist-output.txt)
                archetype="generic"
                focus="code-quality"
                weight=1
                ;;
            dyn-*-output.txt)
                archetype="$slot"
                [[ "$archetype" == dyn-* ]] || archetype="${base%-output.txt}"
                [[ -n "$focus" ]] || focus="code-quality"
                ;;
            cursor-specialist-*-output.txt|codex-specialist-*-output.txt)
                static_slug="$base"
                static_slug="${static_slug#cursor-specialist-}"
                static_slug="${static_slug#codex-specialist-}"
                static_slug="${static_slug%-output.txt}"
                archetype="$static_slug"
                focus=$(static_focus_area "$static_slug")
                weight=1
                ;;
            *)
                archetype="${slot:-${base%-output.txt}}"
                [[ -n "$focus" ]] || focus="code-quality"
                weight=1
                ;;
        esac
        case "$weight" in ''|*[!0-9]*) weight=1 ;; esac
        printf '%s\t%s\t%s\t%s\n' "$base" "$archetype" "$focus" "$weight" >> "$map_file"
    done < "$manifest_file"
}

# scope_drift_check: returns 0 (drift detected, reclassify as OOS) or 1 (keep in-scope).
# Fires only when SCOPE_FILES is a non-empty readable file. Logic:
#   1. Extract path-looking tokens from the block's first (heading) line.
#   2. If no tokens matching path.ext:line on the heading → keep in-scope.
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
    [[ -n "$paths" ]] || return 1  # no path:line token → keep in-scope (conservative)
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
    local prefix="${id%%_*}" n="${id#*_}"
    printf '%s_%s_ACCEPTED=%s\n' "$prefix" "$n" "$accepted" >> "$TALLY_ENV_FILE"
    if [[ "$outcome" == "accepted" ]]; then
        printf '%s_%s_OUTCOME=accepted\n' "$prefix" "$n" >> "$TALLY_ENV_FILE"
    else
        printf '%s_%s_OUTCOME=rejected\n' "$prefix" "$n" >> "$TALLY_ENV_FILE"
        case "$outcome" in
            rejected) printf '%s_%s_REJECTED_SUBTYPE=true_rejected\n' "$prefix" "$n" >> "$TALLY_ENV_FILE" ;;
            neutral) printf '%s_%s_REJECTED_SUBTYPE=neutral\n' "$prefix" "$n" >> "$TALLY_ENV_FILE" ;;
            exonerated) printf '%s_%s_REJECTED_SUBTYPE=exonerated\n' "$prefix" "$n" >> "$TALLY_ENV_FILE" ;;
            *)
                larch_err "tally-code-votes.sh: record_tally_outcome: unexpected outcome for $id: $outcome"
                exit 2
                ;;
        esac
    fi
}

# Voter eligibility is the panel-level count of available voter files. The
# deprecated --both-down flag maps to the 0-judge main-agent path.
ELIGIBLE_VOTERS="${#VOTER_FILES[@]}"
VOTING_SKIPPED_WARNING=""
if [[ "$BOTH_DOWN" == "true" ]]; then
    ELIGIBLE_VOTERS=0
fi
VOTER_PARSE_FAILED_COUNT=0
EFFECTIVE_VOTER_FILES=()
for voter_file in "${VOTER_FILES[@]+"${VOTER_FILES[@]}"}"; do
    diag_file="$(voter_parse_rate_diag_path "$voter_file")"
    if voter_parse_rate_diag_matches_output "$diag_file" "$voter_file"; then
        VOTER_PARSE_FAILED_COUNT=$((VOTER_PARSE_FAILED_COUNT + 1))
    else
        EFFECTIVE_VOTER_FILES+=("$voter_file")
    fi
done
EFFECTIVE_VOTERS=$((ELIGIBLE_VOTERS - VOTER_PARSE_FAILED_COUNT))
(( EFFECTIVE_VOTERS < 0 )) && EFFECTIVE_VOTERS=0

if (( EFFECTIVE_VOTERS == 0 )); then
    for block in "${block_files[@]+"${block_files[@]}"}"; do
        id=$(basename "$block" .md)
        reviewer=$(reviewer_for_block "$block")
        write_classification_tsv_row "$id" "$reviewer" rejected
    done
    VOTING_SKIPPED_WARNING="**⚠ Degraded code-review panel: 0 judges available. Panel tier: main-agent-required. Manual adjudication needed.**"
    printf '# Code Review Voting Tally\n\n' > "$VOTING_TALLY_FILE"
    printf '%s\n\n' "$VOTING_SKIPPED_WARNING" >> "$VOTING_TALLY_FILE"
    if [[ "$NOT_SUBSTANTIVE_COUNT" -gt 0 ]]; then
        printf '**⚠ Degraded code-review panel: %s reviewer slot(s) emitted narrative-only output (NOT_SUBSTANTIVE). Dead slots are shown in the scoreboard below.**\n\n' "$NOT_SUBSTANTIVE_COUNT" >> "$VOTING_TALLY_FILE"
    fi
    if [[ "$VOTER_PARSE_FAILED_COUNT" -gt 0 && "$ELIGIBLE_VOTERS" -gt 0 ]]; then
        printf '**⚠ Degraded code-review panel: %s voter slot(s) emitted narrative-only output (parse-rate ≥80%% JUDGE_ERROR) and were removed from the effective quorum.**\n\n' "$VOTER_PARSE_FAILED_COUNT" >> "$VOTING_TALLY_FILE"
    fi
    emit_kv TALLY_STATUS main-agent-vote-required
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
    emit_kv ELIGIBLE_VOTER_COUNT "$ELIGIBLE_VOTERS"
    emit_kv VOTER_COUNT 0
    emit_kv VOTING_SKIPPED_WARNING "$VOTING_SKIPPED_WARNING"
    [[ -f "$CLASSIFICATION_TSV" ]] && emit_kv FINDINGS_CLASSIFICATION_TSV_FILE "$CLASSIFICATION_TSV"
    exit 0
fi

# Voting path: at least 1 judge available. Tally each block.
score_rows="$WORKDIR/score-rows.tsv"
archetype_map="$WORKDIR/archetype-map.tsv"
: > "$score_rows"
write_archetype_map "$MANIFEST_FILE" "$archetype_map"

{
    printf '# Code Review Voting Tally\n\n'
    EXPECTED_VOTERS=$(expected_voters_for_round "$ROUND_NUM")
    if (( EFFECTIVE_VOTERS < EXPECTED_VOTERS )); then
        tier_label="$(panel_tier "$EFFECTIVE_VOTERS")"
        printf '**⚠ Degraded code-review panel: %s judge(s) available. Panel tier: %s.**\n\n' "$EFFECTIVE_VOTERS" "$tier_label"
    fi
    if [[ "$NOT_SUBSTANTIVE_COUNT" -gt 0 ]]; then
        printf '**⚠ Degraded code-review panel: %s reviewer slot(s) emitted narrative-only output (NOT_SUBSTANTIVE). Dead slots are shown in the scoreboard below.**\n\n' "$NOT_SUBSTANTIVE_COUNT"
    fi
    if [[ "$VOTER_PARSE_FAILED_COUNT" -gt 0 ]]; then
        printf '**⚠ Degraded code-review panel: %s voter slot(s) emitted narrative-only output (parse-rate ≥80%% JUDGE_ERROR) and were removed from the effective quorum.**\n\n' "$VOTER_PARSE_FAILED_COUNT"
    fi
    printf '## Per-finding vote breakdown\n\n'
    printf '| Item | YES | NO | EXON | JERR | Result |\n'
    printf '|---|---:|---:|---:|---:|---|\n'

    for block in "${block_files[@]+"${block_files[@]}"}"; do
        id=$(basename "$block" .md)
        yes=0; no=0; exonerate=0; judge_error=0
        classification_cells=()
        # Code review uses EFFECTIVE_VOTERS, not raw voter-file count, after
        # parse-rate degradation removes narrative-only voter slots.
        for voter_file in "${EFFECTIVE_VOTER_FILES[@]}"; do
            parsed_vote_rating=$(parse_vote_rating_for "$voter_file" "$id")
            vote=$(printf '%s\n' "$parsed_vote_rating" | kv_value PARSED_VOTE)
            correctness=$(printf '%s\n' "$parsed_vote_rating" | kv_value PARSED_CORRECTNESS)
            severity=$(printf '%s\n' "$parsed_vote_rating" | kv_value PARSED_SEVERITY)
            quality=$(printf '%s\n' "$parsed_vote_rating" | kv_value PARSED_QUALITY)
            uncertain=$(printf '%s\n' "$parsed_vote_rating" | kv_value PARSED_UNCERTAIN)
            classification_cells+=("$vote" "$correctness" "$severity" "$quality" "$uncertain")
            case "$vote" in
                YES) yes=$((yes + 1)) ;;
                NO) no=$((no + 1)) ;;
                EXONERATE) exonerate=$((exonerate + 1)) ;;
                *) judge_error=$((judge_error + 1)) ;;
            esac
        done

        result=$(classify_result "$yes" "$no" "$exonerate" "$EFFECTIVE_VOTERS")
        case "$result" in
            accepted|rejected|exonerated|neutral) ;;
            *)
                larch_err "tally-code-votes.sh: unknown classify_result outcome for $id: $result"
                exit 2
                ;;
        esac
        printf '| %s | %s | %s | %s | %s | %s |\n' "$id" "$yes" "$no" "$exonerate" "$judge_error" "$result"

        reviewer=$(reviewer_for_block "$block")
        write_classification_tsv_row "$id" "$reviewer" "$result" "${classification_cells[@]+"${classification_cells[@]}"}"

        # Code review supports OOS_N headings and legacy FINDING_N headings
        # tagged with [OUT_OF_SCOPE].
        is_oos=false
        if [[ "$id" == OOS_* ]] || head -n1 "$block" | grep -Fq '[OUT_OF_SCOPE]'; then
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
        printf '%s' "$reviewer" | awk -v kind="$kind" -v result="$result" -F',' '
        {
            delete seen
            for (i = 1; i <= NF; i++) {
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", $i)
                if ($i != "" && !($i in seen)) {
                    seen[$i] = 1
                    print $i "\t" kind "\t" result
                }
            }
        }' >> "$score_rows"

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
                REJECTED_COUNT=$((REJECTED_COUNT + 1))
                case "$result" in
                    rejected)
                        {
                            printf '### [rejected] %s\n\n' "$id"
                            printf '%s\n\n' "**Rejected subtype:** dismissed (no acceptance threshold met)"
                            cat "$block"
                            printf '\nVote tally: YES=%s NO=%s EXON=%s JUDGE_ERROR=%s\n\n' "$yes" "$no" "$exonerate" "$judge_error"
                        } >> "$REJECTED_FINDINGS_FILE"
                        ;;
                    exonerated)
                        EXONERATED_COUNT=$((EXONERATED_COUNT + 1))
                        {
                            printf '### [rejected] %s\n\n' "$id"
                            printf '%s\n\n' "**Rejected subtype:** exonerated (concern noted, not implemented in this PR)"
                            cat "$block"
                            printf '\nVote tally: YES=%s NO=%s EXON=%s JUDGE_ERROR=%s\n\n' "$yes" "$no" "$exonerate" "$judge_error"
                        } >> "$REJECTED_FINDINGS_FILE"
                        ;;
                    neutral)
                        NEUTRAL_COUNT=$((NEUTRAL_COUNT + 1))
                        {
                            printf '### [rejected] %s\n\n' "$id"
                            printf '%s\n\n' "**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)"
                            cat "$block"
                            printf '\nVote tally: YES=%s NO=%s EXON=%s JUDGE_ERROR=%s\n\n' "$yes" "$no" "$exonerate" "$judge_error"
                        } >> "$REJECTED_FINDINGS_FILE"
                        ;;
                esac
                record_tally_outcome "$id" false "$result"
            fi
        else
            # OOS item
            cat "$block" >> "$OOS_FILE"
            printf '\nVote tally: YES=%s NO=%s EXON=%s JUDGE_ERROR=%s Result=%s\n\n' "$yes" "$no" "$exonerate" "$judge_error" "$result" >> "$OOS_FILE"
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
    printf '| Reviewer | Proposed | Accepted | Exonerated | Rejected | OOS-Proposed | OOS-Accepted | OOS-Exonerated | OOS-Rejected | Score | Status |\n'
    printf '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|\n'
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
          label=reviewer
          sub(/-output\.txt$/, "", label)
          sub(/\.txt$/, "", label)
          score=accepted[reviewer]+0 + oos_accepted[reviewer]+0 - rejected[reviewer]+0 - oos_rejected[reviewer]+0
          printf "| %s | %d | %d | %d | %d | %d | %d | %d | %d | %d | STATUS=OK |\n",
            label, proposed[reviewer]+0, accepted[reviewer]+0, neutral[reviewer]+0,
            rejected[reviewer]+0, oos_proposed[reviewer]+0, oos_accepted[reviewer]+0,
            oos_neutral[reviewer]+0, oos_rejected[reviewer]+0, score
        }
      }
    ' "$score_rows" | sort
} > "$VOTING_TALLY_FILE"

# Append zero-count rows for manifest entries that produced no score_rows, including
# narrative-only NOT_SUBSTANTIVE slots and dynamic/other manifest slots that had no
# accepted, scoreboard-neutral/exonerated, rejected, or OOS findings. Missing collector metadata falls
# back to STATUS=OK.
# Uses awk (not bash arrays) for bash 3.2 portability.
if [[ -n "$MANIFEST_FILE" && -f "$MANIFEST_FILE" ]]; then
    _dead_rows=$(awk -v collector_file="${COLLECTOR_RESULTS_FILE:-/dev/null}" \
        -v score_file="$score_rows" \
        -v manifest_file="$MANIFEST_FILE" \
        '
        function norm_base(b,    stem) {
            sub(/^.*\//, "", b)
            if (b ~ /\.txt$/) {
                stem = b; sub(/\.txt$/, "", stem)
                while (stem ~ /-(phase2|phase3|retry)$/) sub(/-(phase2|phase3|retry)$/, "", stem)
                return stem ".txt"
            }
            stem = b
            while (stem ~ /-(phase2|phase3|retry)$/) sub(/-(phase2|phase3|retry)$/, "", stem)
            return stem
        }
        BEGIN {
            cr_file = ""; cr_status = ""
            while ((getline line < collector_file) > 0) {
                if (line == "") {
                    if (cr_file != "" && cr_status != "") {
                        n = split(cr_file, parts, "/"); b = parts[n]
                        b = norm_base(b)
                        collector_status[b] = cr_status
                    }
                    cr_file = ""; cr_status = ""
                } else if (substr(line,1,14) == "REVIEWER_FILE=") {
                    cr_file = substr(line,15)
                } else if (substr(line,1,7) == "STATUS=") {
                    cr_status = substr(line,8)
                }
            }
            if (cr_file != "" && cr_status != "") {
                n = split(cr_file, parts, "/"); b = parts[n]
                b = norm_base(b); collector_status[b] = cr_status
            }
            close(collector_file)
            while ((getline line < score_file) > 0) {
                n = split(line, f, "\t")
                if (n >= 1 && f[1] != "") seen[norm_base(f[1])] = 1
            }
            close(score_file)
            while ((getline row < manifest_file) > 0) {
                if (row == "") continue
                b = row
                gsub(/.*"output":"/, "", b); gsub(/".*/, "", b)
                n = split(b, parts, "/"); base = parts[n]
                normed = norm_base(base)
                if (!(normed in seen)) {
                    st = (normed in collector_status) ? collector_status[normed] : "OK"
                    label = normed; sub(/-output\.txt$/, "", label); sub(/\.txt$/, "", label)
                    printf "| %s | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS=%s |\n", label, st
                }
            }
        }
        ' /dev/null)
    if [[ -n "$_dead_rows" ]]; then
        printf '%s\n' "$_dead_rows" >> "$VOTING_TALLY_FILE"
    fi
fi

if [[ -n "$MANIFEST_FILE" && -f "$MANIFEST_FILE" ]]; then
    awk -F '\t' '
      function norm(base, stem) {
        sub(/^.*\//, "", base)
        if (base ~ /\.txt$/) {
          stem = base
          sub(/\.txt$/, "", stem)
          while (stem ~ /-(phase2|phase3|retry)$/) sub(/-(phase2|phase3|retry)$/, "", stem)
          return stem ".txt"
        }
        stem = base
        while (stem ~ /-(phase2|phase3|retry)$/) sub(/-(phase2|phase3|retry)$/, "", stem)
        return stem
      }
      FNR == NR {
        base=$1
        if (!(base in seen)) {
          order[++n]=base
          seen[base]=1
        }
        archetype[base]=$2
        focus[base]=$3
        weight[base]=$4
        next
      }
      {
        base=norm($1)
        if ($2 != "finding") next
        if ($3 == "accepted") {
          total[base]++
          accepted[base]++
        } else if ($3 == "neutral" || $3 == "exonerated") {
          total[base]++
        } else if ($3 == "rejected") {
          total[base]++
          rejected[base]++
        }
      }
      END {
        printf "archetype_name\tfocus_area\tweight\tfindings_total\tfindings_accepted\tfindings_rejected\tyield_ratio\n"
        for (i = 1; i <= n; i++) {
          base=order[i]
          t=total[base]+0
          a=accepted[base]+0
          r=rejected[base]+0
          ratio = (t == 0 ? "n/a" : sprintf("%.6f", a / t))
          printf "%s\t%s\t%s\t%d\t%d\t%d\t%s\n", archetype[base], focus[base], weight[base], t, a, r, ratio
        }
      }
    ' "$archetype_map" "$score_rows" > "$YIELD_TSV_FILE"

    while IFS= read -r orphan_base || [[ -n "$orphan_base" ]]; do
        [[ -n "$orphan_base" ]] || continue
        emit_kv WARN "yield TSV missing manifest entry for reviewer basename: $orphan_base"
    done < <(
        awk -F '\t' '
          function norm(base, stem) {
            sub(/^.*\//, "", base)
            if (base ~ /\.txt$/) {
              stem = base
              sub(/\.txt$/, "", stem)
              while (stem ~ /-(phase2|phase3|retry)$/) sub(/-(phase2|phase3|retry)$/, "", stem)
              return stem ".txt"
            }
            stem = base
            while (stem ~ /-(phase2|phase3|retry)$/) sub(/-(phase2|phase3|retry)$/, "", stem)
            return stem
          }
          FNR == NR { seen[$1]=1; next }
          {
            base=norm($1)
            if (!(base in seen) && !reported[base]++) print base
          }
        ' "$archetype_map" "$score_rows"
    )
fi

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
emit_kv ELIGIBLE_VOTER_COUNT "$ELIGIBLE_VOTERS"
emit_kv VOTER_COUNT "$EFFECTIVE_VOTERS"
if [[ -n "$MANIFEST_FILE" && -f "$YIELD_TSV_FILE" ]]; then
    emit_kv YIELD_TSV_FILE "$YIELD_TSV_FILE"
fi
[[ -f "$CLASSIFICATION_TSV" ]] && emit_kv FINDINGS_CLASSIFICATION_TSV_FILE "$CLASSIFICATION_TSV"
