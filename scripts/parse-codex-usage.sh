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

usage_err_file=$(mktemp "${TMPDIR:-/tmp}/parse-codex-usage.XXXXXX")
trap 'rm -f "$usage_err_file"' EXIT
usage_tsv=$(
    jq -nRr '
      def num($v): if $v == null then 0 else ($v | tonumber) end;
      def tokenish($v):
        ($v.input_tokens?, $v.cached_input_tokens?, $v.output_tokens?,
         $v.input_tokens_details.cached_tokens?,
         $v.msg.input_tokens?, $v.msg.cached_input_tokens?, $v.msg.output_tokens?,
         $v.msg.input_tokens_details.cached_tokens?) | select(. != null);
      def has_tokenish($v): try ([tokenish($v)] | length > 0) catch false;
      def input_of($o):
        num($o.msg.usage.input_tokens // $o.msg.input_tokens // $o.usage.input_tokens // $o.input_tokens // 0);
      def cached_of($o):
        num($o.msg.usage.cached_input_tokens
          // $o.msg.usage.input_tokens_details.cached_tokens
          // $o.msg.cached_input_tokens
          // $o.msg.input_tokens_details.cached_tokens
          // $o.usage.cached_input_tokens
          // $o.usage.input_tokens_details.cached_tokens
          // $o.cached_input_tokens
          // $o.input_tokens_details.cached_tokens
          // 0);
      def output_of($o):
        num($o.msg.usage.output_tokens // $o.msg.output_tokens // $o.usage.output_tokens // $o.output_tokens // 0);
      def usage_row($o):
        {input: input_of($o), cached: cached_of($o), output: output_of($o)};
      def fail_if_cached_exceeds_input($u):
        if $u.cached > $u.input then
          error("cached_tokens exceeds input_tokens; fail-closed")
        else
          $u
        end;
      [inputs | fromjson? | select(type == "object")] as $events
      | ([ $events[] | select(.type == "token_usage" and has_tokenish(.)) ] | last) as $rollup
      | if $rollup != null then
          (usage_row($rollup) | fail_if_cached_exceeds_input(.)) as $usage
          | [1, $usage.input, $usage.cached, $usage.output] | @tsv
        else
          reduce ($events[] | select(has_tokenish(.msg.usage) or has_tokenish(.usage))) as $o
            ({count:0, input:0, cached:0, output:0};
              (usage_row($o) | fail_if_cached_exceeds_input(.)) as $usage
              | .count += 1
              | .input += $usage.input
              | .cached += $usage.cached
              | .output += $usage.output)
          | [.count, .input, .cached, .output] | @tsv
        end
    ' "$EVENTS_FILE" 2>"$usage_err_file"
) || {
    if grep -Fq 'cached_tokens exceeds input_tokens; fail-closed' "$usage_err_file" 2>/dev/null; then
        larch_err "parse-codex-usage.sh: cached_tokens exceeds input_tokens; fail-closed"
    elif [[ -s "$usage_err_file" ]]; then
        larch_err "parse-codex-usage.sh: jq failed"
    else
        larch_err "parse-codex-usage.sh: no usage events"
    fi
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
