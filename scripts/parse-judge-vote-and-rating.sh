#!/usr/bin/env bash
# Parse one judge vote line plus optional forensic rating axes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

if [[ $# -ne 2 ]]; then
    larch_err "usage: parse-judge-vote-and-rating.sh <voter_file> <ballot_id>"
    exit 2
fi

voter_file="$1"
ballot_id="$2"

if [[ ! -r "$voter_file" ]]; then
    larch_err "parse-judge-vote-and-rating.sh: voter file is missing or unreadable: $voter_file"
    exit 2
fi

parsed=$(
    awk -v id="$ballot_id" '
      function valid_correctness(v) { return v ~ /^(true|partially-true|false-positive|uncertain)$/ }
      function valid_severity(v) { return v ~ /^(blocker|major|minor|nit|uncertain)$/ }
      function valid_quality(v) { return v ~ /^(excellent|good|adequate|weak|no-fix|uncertain)$/ }
      function valid_uncertain(v) { return v ~ /^(true|false)$/ }
      function reset_fields() {
        vote=""; correctness=""; severity=""; quality=""; uncertain_token="";
      }
      BEGIN {
        reset_fields()
        upper_id=toupper(id)
      }
      toupper($0) ~ ("^" upper_id ":[[:space:]]*") {
        reset_fields()
        line=$0
        sub(/^[^:]+:[[:space:]]*/, "", line)
        scoped=line
        delim=index(scoped, " -- ")
        if (delim > 0) {
          scoped=substr(scoped, 1, delim - 1)
        }
        upper=toupper(scoped)
        if (match(upper, /^(YES|NO|EXONERATE)([[:space:]-]|$)/)) {
          vote=substr(upper, RSTART, RLENGTH)
          sub(/([[:space:]-]).*$/, "", vote)
        }
        n=split(scoped, parts, /[[:space:]]+/)
        for (i = 1; i <= n; i++) {
          if (parts[i] ~ /^CORRECTNESS=/) {
            v=parts[i]; sub(/^CORRECTNESS=/, "", v)
            if (valid_correctness(v)) correctness=v
            else correctness=""
          } else if (parts[i] ~ /^SEVERITY=/) {
            v=parts[i]; sub(/^SEVERITY=/, "", v)
            if (valid_severity(v)) severity=v
            else severity=""
          } else if (parts[i] ~ /^QUALITY=/) {
            v=parts[i]; sub(/^QUALITY=/, "", v)
            if (valid_quality(v)) quality=v
            else quality=""
          } else if (parts[i] ~ /^UNCERTAIN=/) {
            v=parts[i]; sub(/^UNCERTAIN=/, "", v)
            if (valid_uncertain(v)) uncertain_token=v
            else uncertain_token=""
          }
        }
      }
      END {
        uncertain="true"
        if (correctness != "" && severity != "" && quality != "" && uncertain_token != "") {
          uncertain=uncertain_token
        }
        printf "%s\t%s\t%s\t%s\t%s\n", vote, correctness, severity, quality, uncertain
      }
    ' "$voter_file"
)

parsed_vote=$(printf '%s\n' "$parsed" | awk -F '\t' '{ print $1 }')
parsed_correctness=$(printf '%s\n' "$parsed" | awk -F '\t' '{ print $2 }')
parsed_severity=$(printf '%s\n' "$parsed" | awk -F '\t' '{ print $3 }')
parsed_quality=$(printf '%s\n' "$parsed" | awk -F '\t' '{ print $4 }')
parsed_uncertain=$(printf '%s\n' "$parsed" | awk -F '\t' '{ print $5 }')

emit_kv PARSED_VOTE "$parsed_vote"
emit_kv PARSED_CORRECTNESS "$parsed_correctness"
emit_kv PARSED_SEVERITY "$parsed_severity"
emit_kv PARSED_QUALITY "$parsed_quality"
emit_kv PARSED_UNCERTAIN "$parsed_uncertain"
