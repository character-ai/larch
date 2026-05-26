#!/usr/bin/env bash
# parse-codex-usage.sh — Sum Codex --json usage events into token buckets.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-quiet.sh"

usage_err() {
    larch_err "parse-codex-usage.sh: usage error"
}

if [ "$#" -ne 1 ]; then
    usage_err
    exit 2
fi

EVENTS_FILE=$1
if [ ! -r "$EVENTS_FILE" ] || [ ! -s "$EVENTS_FILE" ]; then
    larch_err "parse-codex-usage.sh: events file missing"
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    larch_err "parse-codex-usage.sh: jq not found"
    exit 1
fi

usage_tsv=$(
    jq -nRr '
      def num($v): ($v | tonumber? // 0);
      reduce (inputs | fromjson? | select(type == "object")) as $o
        ({count:0, input:0, cached:0, output:0};
          ($o.msg.usage? // $o.usage? // (if ($o.input_tokens? // $o.cached_input_tokens? // $o.output_tokens? // null) == null then null else {} end)) as $usage |
          if $usage == null then
            .
          else
            .count += 1
            | .input += num($o.msg.usage.input_tokens // $o.usage.input_tokens // $o.input_tokens // 0)
            | .cached += num($o.msg.usage.cached_input_tokens // $o.msg.usage.input_tokens_details.cached_tokens // $o.usage.cached_input_tokens // $o.usage.input_tokens_details.cached_tokens // $o.cached_input_tokens // $o.input_tokens_details.cached_tokens // 0)
            | .output += num($o.msg.usage.output_tokens // $o.usage.output_tokens // $o.output_tokens // 0)
          end)
      | "\(.count)\t\(.input)\t\(.cached)\t\(.output)"
    ' "$EVENTS_FILE" 2>/dev/null
) || {
    larch_err "parse-codex-usage.sh: no usage events"
    exit 1
}

IFS=$'\t' read -r usage_count input_tokens cached_tokens output_tokens <<EOF
$usage_tsv
EOF

case "${usage_count:-}" in ''|*[!0-9]*) usage_count=0 ;; esac
case "${input_tokens:-}" in ''|*[!0-9]*) input_tokens=0 ;; esac
case "${cached_tokens:-}" in ''|*[!0-9]*) cached_tokens=0 ;; esac
case "${output_tokens:-}" in ''|*[!0-9]*) output_tokens=0 ;; esac

if [ "$usage_count" -eq 0 ]; then
    larch_err "parse-codex-usage.sh: no usage events"
    exit 1
fi

if [ "$cached_tokens" -gt "$input_tokens" ]; then
    larch_err "parse-codex-usage.sh: cached_tokens exceeds input_tokens; fail-closed"
    exit 1
fi

uncached_input=$((input_tokens - cached_tokens))
total=$((uncached_input + cached_tokens + output_tokens))
if [ "$total" -eq 0 ]; then
    larch_err "parse-codex-usage.sh: no usage events"
    exit 1
fi

printf 'INPUT=%s\n' "$uncached_input"
printf 'CACHED_INPUT=%s\n' "$cached_tokens"
printf 'OUTPUT=%s\n' "$output_tokens"
printf 'TOTAL=%s\n' "$total"
