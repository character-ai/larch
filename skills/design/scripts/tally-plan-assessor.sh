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
    while IFS= read -r line || [[ -n "$line" ]]; do
        local stripped
        stripped=$(strip_md_bold "$line")
        case "$stripped" in
            ASSESSMENT:*|Assessment:*|assessment:*)
                verdict="${stripped#*:}"
                verdict="${verdict#"${verdict%%[![:space:]]*}"}"
                verdict="${verdict%"${verdict##*[![:space:]]}"}"
                verdict=$(printf '%s' "$verdict" | tr '[:lower:]' '[:upper:]')
                in_reason=0
                in_qual=0
                ;;
            REASONING:*)
                reasoning="${stripped#*:}"
                reasoning="${reasoning#"${reasoning%%[![:space:]]*}"}"
                in_reason=1
                in_qual=0
                ;;
            QUALIFICATIONS:*)
                qualifications="${stripped#*:}"
                qualifications="${qualifications#"${qualifications%%[![:space:]]*}"}"
                in_qual=1
                in_reason=0
                ;;
            *)
                if [[ "$in_reason" -eq 1 ]]; then
                    if [[ -n "$reasoning" ]]; then reasoning="$reasoning "; fi
                    reasoning="$reasoning$line"
                elif [[ "$in_qual" -eq 1 ]]; then
                    if [[ -n "$qualifications" ]]; then qualifications="$qualifications "; fi
                    qualifications="$qualifications$line"
                fi
                ;;
        esac
    done <"$file"
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
qual_worse=""
reason_worse=""

for path in "$CLAUDE_OUTPUT" "$CODEX_OUTPUT" "$CURSOR_OUTPUT"; do
    ASSESS_VERDICT="" ASSESS_REASON="" ASSESS_QUAL=""
    if parse_assessment "$path"; then
        successful=$((successful + 1))
        case "$ASSESS_VERDICT" in
            BETTER) better=$((better + 1)) ;;
            WORSE)
                worse=$((worse + 1))
                if [[ -z "$qual_worse" && -n "$ASSESS_QUAL" ]]; then qual_worse="$ASSESS_QUAL"; fi
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

mkdir -p "$(dirname "$OUTPUT")"
tmp_out=$(mktemp "$(dirname "$OUTPUT")/.assessor-verdict.XXXXXX")
tmp_env=$(mktemp "$(dirname "$OUTPUT")/.assessor-verdict-env.XXXXXX")

if [[ "$worse_majority" == true ]]; then
    justification="${reason_worse:-Multiple assessors judged the current plan worse than the previous round.}"
    if [[ ${#justification} -gt 500 ]]; then
        justification="${justification:0:497}..."
    fi
    printf 'WORSE: %s\n' "$justification" >"$tmp_out"
    assessor_verdict=worse-majority
else
    printf 'NOT_WORSE\n' >"$tmp_out"
    assessor_verdict=not-worse
fi

qual_summary="${qual_worse:-Assessors found no WORSE-majority consensus.}"
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
