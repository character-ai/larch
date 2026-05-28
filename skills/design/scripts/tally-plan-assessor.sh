#!/usr/bin/env bash
# tally-plan-assessor.sh — Tally 3-assessor BETTER/WORSE/TIE votes into compact verdict files.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

DESIGN_TMPDIR=""
ROUND_NUM=""
CLAUDE_OUTPUT=""
CURSOR_OUTPUT=""
CODEX_OUTPUT=""
OUTPUT=""

usage() {
    larch_err "Usage: tally-plan-assessor.sh --design-tmpdir DIR --round-num N --claude-output PATH --cursor-output PATH --codex-output PATH --output PATH"
}

strip_md_bold() {
    local line="$1"
    line="${line#"${line%%[![:space:]]*}"}"
    line=$(printf '%s' "$line" | tr -d '*')
    printf '%s' "$line"
}

parse_assessment() {
    local file="$1"
    local line verdict="" reasoning="" qualifications="" in_reason=0 in_qual=0
    [[ -f "$file" && -s "$file" ]] || return 1
    shopt -s nocasematch
    while IFS= read -r line || [[ -n "$line" ]]; do
        local stripped
        stripped=$(strip_md_bold "$line")
        if [[ "$stripped" =~ ^[[:space:]]*assessment[[:space:]]*[:=][[:space:]]*(.*)$ ]]; then
                verdict="${BASH_REMATCH[1]}"
                verdict="${verdict#"${verdict%%[![:space:]]*}"}"
                verdict="${verdict%"${verdict##*[![:space:]]}"}"
                verdict=$(printf '%s' "$verdict" | tr '[:lower:]' '[:upper:]')
                reasoning=""
                qualifications=""
                in_reason=0
                in_qual=0
        elif [[ "$stripped" =~ ^[[:space:]]*reasoning[[:space:]]*[:=][[:space:]]*(.*)$ ]]; then
                reasoning="${BASH_REMATCH[1]}"
                reasoning="${reasoning#"${reasoning%%[![:space:]]*}"}"
                in_reason=1
                in_qual=0
        elif [[ "$stripped" =~ ^[[:space:]]*qualifications[[:space:]]*[:=][[:space:]]*(.*)$ ]]; then
                qualifications="${BASH_REMATCH[1]}"
                qualifications="${qualifications#"${qualifications%%[![:space:]]*}"}"
                in_qual=1
                in_reason=0
        else
                if [[ "$in_reason" -eq 1 ]]; then
                    if [[ -n "$reasoning" ]]; then reasoning="$reasoning "; fi
                    reasoning="$reasoning$line"
                elif [[ "$in_qual" -eq 1 ]]; then
                    if [[ -n "$qualifications" ]]; then qualifications="$qualifications "; fi
                    qualifications="$qualifications$line"
                fi
        fi
    done <"$file"
    shopt -u nocasematch
    case "$verdict" in
        BETTER|WORSE|TIE)
            ASSESS_VERDICT="$verdict"
            ASSESS_REASON="$reasoning"
            ASSESS_QUAL="$qualifications"
            return 0
            ;;
        *) return 1 ;;
    esac
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --round-num) ROUND_NUM="${2:?}"; shift 2 ;;
        --claude-output) CLAUDE_OUTPUT="${2:?}"; shift 2 ;;
        --cursor-output) CURSOR_OUTPUT="${2:?}"; shift 2 ;;
        --codex-output) CODEX_OUTPUT="${2:?}"; shift 2 ;;
        --output) OUTPUT="${2:?}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) larch_err "tally-plan-assessor.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$DESIGN_TMPDIR" && -n "$ROUND_NUM" && -n "$OUTPUT" ]] || { usage; exit 2; }

better=0 worse=0 tie=0 successful=0
declare -a qual_worse_list=()
reason_worse=""

add_distinct_qualification() {
    local candidate="$1" existing=""
    [[ -n "$candidate" ]] || return 0
    for existing in "${qual_worse_list[@]:-}"; do
        [[ "$existing" == "$candidate" ]] && return 0
    done
    qual_worse_list+=("$candidate")
}

for path in "$CLAUDE_OUTPUT" "$CODEX_OUTPUT" "$CURSOR_OUTPUT"; do
    ASSESS_VERDICT="" ASSESS_REASON="" ASSESS_QUAL=""
    if parse_assessment "$path"; then
        successful=$((successful + 1))
        case "$ASSESS_VERDICT" in
            BETTER) better=$((better + 1)) ;;
            WORSE)
                worse=$((worse + 1))
                add_distinct_qualification "$ASSESS_QUAL"
                if [[ -n "$ASSESS_REASON" ]]; then
                    if [[ -n "$reason_worse" ]]; then reason_worse="$reason_worse "; fi
                    reason_worse="$reason_worse$ASSESS_REASON"
                fi
                ;;
            TIE) tie=$((tie + 1)) ;;
        esac
    fi
done

worse_majority=false
if (( successful == 3 && worse >= 2 )); then worse_majority=true; fi
if (( successful == 2 && worse == 2 )); then worse_majority=true; fi
if (( successful == 1 && worse == 1 )); then worse_majority=true; fi

degraded=false
if (( successful == 0 )); then degraded=true; fi

qual_summary=""
if ((${#qual_worse_list[@]} > 0)); then
    qual_summary="${qual_worse_list[0]}"
    if ((${#qual_worse_list[@]} > 1)); then
        local_idx=1
        while (( local_idx < ${#qual_worse_list[@]} )); do
            qual_summary="${qual_summary} | ${qual_worse_list[$local_idx]}"
            local_idx=$((local_idx + 1))
        done
    fi
fi

mkdir -p "$(dirname "$OUTPUT")"
tmp_out=$(mktemp "$(dirname "$OUTPUT")/.assessor-verdict.XXXXXX")
tmp_env=$(mktemp "$(dirname "$OUTPUT")/.assessor-verdict-env.XXXXXX")

if [[ "$worse_majority" == true ]]; then
    justification="${reason_worse:-Multiple assessors judged the current plan worse than the previous round.}"
    if [[ ${#justification} -gt 500 ]]; then
        justification="${justification:0:497}..."
    fi
    printf 'WORSE: %s\n' "$justification" >"$tmp_out"
    assessor_verdict='worse-majority'
else
    printf 'NOT_WORSE\n' >"$tmp_out"
    assessor_verdict='not-worse'
fi

if [[ "$worse_majority" == true ]]; then
    qual_summary="${qual_summary:-WORSE-majority assessors supplied no qualifications.}"
else
    qual_summary="${qual_summary:-Assessors found no WORSE-majority consensus.}"
fi
if [[ ${#qual_summary} -gt 240 ]]; then
    qual_summary="${qual_summary:0:237}..."
fi
{
    printf 'ASSESSOR_VERDICT=%s\n' "$assessor_verdict"
    printf 'BETTER_VOTES=%s\n' "$better"
    printf 'WORSE_VOTES=%s\n' "$worse"
    printf 'TIE_VOTES=%s\n' "$tie"
    printf 'EFFECTIVE_ASSESSORS=%s\n' "$successful"
    printf 'DEGRADED_DEFAULT_OPEN=%s\n' "$degraded"
    printf 'QUALIFICATIONS_SUMMARY=%s\n' "$qual_summary"
} >"$tmp_env"

mv -f "$tmp_out" "$OUTPUT"
mv -f "$tmp_env" "${OUTPUT}.env"

emit_kv ASSESSOR_VERDICT "$assessor_verdict"
emit_kv EFFECTIVE_ASSESSORS "$successful"
emit_kv WORSE_VOTES "$worse"
emit_kv BETTER_VOTES "$better"
emit_kv TIE_VOTES "$tie"
emit_kv ASSESSOR_VERDICT_FILE "$OUTPUT"
emit_kv ASSESSOR_VERDICT_ENV "${OUTPUT}.env"
exit 0
