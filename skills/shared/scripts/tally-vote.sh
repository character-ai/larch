#!/usr/bin/env bash
# tally-vote.sh — Apply review vote thresholds to ballot findings.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

usage() { echo "Usage: tally-vote.sh --ballot-file FILE --voter-files FILE..." >&2; }

BALLOT_FILE=""
VOTER_FILES=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --ballot-file) BALLOT_FILE="${2:?--ballot-file requires a value}"; shift 2 ;;
        --voter-files)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do VOTER_FILES+=("$1"); shift; done
            ;;
        --help) usage; exit 0 ;;
        *) echo "tally-vote.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

[[ -n "$BALLOT_FILE" && -f "$BALLOT_FILE" ]] || { echo "tally-vote.sh: --ballot-file must name a file" >&2; exit 2; }

parse_out=$("$SCRIPT_DIR/ballot-parse.sh" --ballot-file "$BALLOT_FILE")
count=$(printf '%s\n' "$parse_out" | awk -F= '$1=="FINDING_COUNT"{print $2}')
count=${count:-0}

idx=1
while [[ "$idx" -le "$count" ]]; do
    yes=0
    no=0
    exon=0
    for vf in "${VOTER_FILES[@]}"; do
        [[ -f "$vf" ]] || continue
        vote=$(awk -v n="$idx" '
            BEGIN { vote="" }
            $0 ~ ("FINDING_" n) {
                if ($0 ~ /EXONERATE/) vote="EXONERATE";
                else if ($0 ~ /YES/) vote="YES";
                else if ($0 ~ /NO/) vote="NO";
            }
            END { print vote }
        ' "$vf")
        case "$vote" in
            YES) yes=$((yes + 1)) ;;
            NO) no=$((no + 1)) ;;
            EXONERATE) exon=$((exon + 1)) ;;
        esac
    done
    accepted=false
    if [[ "$yes" -ge 2 ]]; then
        accepted=true
    elif [[ "$yes" -eq 1 && "${#VOTER_FILES[@]}" -eq 1 ]]; then
        accepted=true
    fi
    printf 'FINDING_%s_ACCEPTED=%s\n' "$idx" "$accepted"
    printf 'FINDING_%s_VOTES_YES=%s\n' "$idx" "$yes"
    printf 'FINDING_%s_VOTES_NO=%s\n' "$idx" "$no"
    printf 'FINDING_%s_VOTES_EXONERATE=%s\n' "$idx" "$exon"
    idx=$((idx + 1))
done
printf 'FINDING_COUNT=%s\n' "$count"
