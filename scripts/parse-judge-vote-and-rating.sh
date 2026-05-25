#!/usr/bin/env bash
# Parse one judge vote line plus forensic rating tokens for one ballot id.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
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
      function valid_correctness(v) {
        return v == "true" || v == "partially-true" || v == "false-positive" || v == "uncertain"
      }
      function valid_severity(v) {
        return v == "blocker" || v == "major" || v == "minor" || v == "nit" || v == "uncertain"
      }
      function valid_quality(v) {
        return v == "excellent" || v == "good" || v == "adequate" || v == "weak" || v == "no-fix" || v == "uncertain"
      }
      function reset_match() {
        vote = ""
        correctness = ""
        severity = ""
        quality = ""
        uncertain_token = ""
      }
      BEGIN {
        reset_match()
        id_upper = toupper(id)
        prefix = "^" id_upper ":[[:space:]]*"
      }
      {
        line = $0
        upper = toupper(line)
        if (upper !~ prefix) {
          next
        }

        reset_match()
        rest = line
        sub(/^[^:]*:[[:space:]]*/, "", rest)
        token = rest
        sub(/^[[:space:]]*/, "", token)
        sub(/[[:space:]-].*$/, "", token)
        token_upper = toupper(token)
        if (token_upper == "YES" || token_upper == "NO" || token_upper == "EXONERATE") {
          vote = token_upper
        }

        n = split(rest, parts, /[[:space:]]+/)
        for (i = 1; i <= n; i++) {
          part = parts[i]
          if (part ~ /^CORRECTNESS=/) {
            value = part
            sub(/^CORRECTNESS=/, "", value)
            correctness = valid_correctness(value) ? value : ""
          } else if (part ~ /^SEVERITY=/) {
            value = part
            sub(/^SEVERITY=/, "", value)
            severity = valid_severity(value) ? value : ""
          } else if (part ~ /^QUALITY=/) {
            value = part
            sub(/^QUALITY=/, "", value)
            quality = valid_quality(value) ? value : ""
          } else if (part ~ /^UNCERTAIN=/) {
            value = part
            sub(/^UNCERTAIN=/, "", value)
            uncertain_token = (value == "true" || value == "false") ? value : ""
          }
        }
      }
      END {
        uncertain = "true"
        if (correctness != "" && severity != "" && quality != "" && uncertain_token == "false") {
          uncertain = "false"
        }
        printf "%s\034%s\034%s\034%s\034%s\n", vote, correctness, severity, quality, uncertain
      }
    ' "$voter_file"
)

IFS=$'\034' read -r parsed_vote parsed_correctness parsed_severity parsed_quality parsed_uncertain <<< "$parsed"

emit_kv PARSED_VOTE "$parsed_vote"
emit_kv PARSED_CORRECTNESS "$parsed_correctness"
emit_kv PARSED_SEVERITY "$parsed_severity"
emit_kv PARSED_QUALITY "$parsed_quality"
emit_kv PARSED_UNCERTAIN "$parsed_uncertain"
