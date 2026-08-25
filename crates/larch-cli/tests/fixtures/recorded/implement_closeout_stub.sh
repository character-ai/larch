#!/bin/sh
set -eu

tmpdir=${IMPLEMENT_TMPDIR:?}

record_event() {
  command_key="$1 $2"
  if [ "$command_key" = "final-report write" ]; then
    rendered="final-report write --implement-tmpdir $4"
    cost_rate=${LARCH_CLAUDE_INPUT_RATE_PER_M-}
    shift 4
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --print-stdout)
          rendered="$rendered --print-stdout"
          ;;
        --cost-overrides-json)
          shift
          case "$1" in
            *'"LARCH_CLAUDE_INPUT_RATE_PER_M":"1.25"'*) cost_rate=1.25 ;;
          esac
          ;;
      esac
      shift
    done
    printf 'ARGV=%s\n' "$rendered"
    printf 'COST_RATE=%s\n' "$cost_rate"
    printf 'CLAUDE_CODE_EFFORT=%s\n' "${CLAUDE_CODE_EFFORT_LEVEL-}"
    printf 'ASSESSMENT_MODEL=%s\n' "${LARCH_EXEC_ISSUE_ASSESSMENT_MODEL-}"
  else
    printf 'ARGV=%s\n' "$*"
  fi
  printf 'TOKEN_SESSION=%s\n' "${LARCH_TOKEN_SESSION_ID-}"
  printf 'CLAUDE_SOURCE=%s\n' "${LARCH_CLAUDE_SOURCE_FILE-}"
  printf 'TIMING_LEDGER=%s\n' "${LARCH_TIMING_LEDGER-}"
  if [ "$command_key" = "slack issue-announce" ]; then
    if [ "${LARCH_SLACK_WEBHOOK_URL-}" = "fixture-webhook" ]; then
      printf 'SLACK_WEBHOOK_PRESENT=true\n'
    else
      printf 'SLACK_WEBHOOK_PRESENT=false\n'
    fi
  fi
}

record_event "$@" >> "$tmpdir/child-events.log"

case "$1 $2" in
  "timing telemetry-mark")
    exit 0
    ;;
  "review-and-fix write-rejected")
    rc=0
    if [ -f "$tmpdir/step16-exit" ]; then
      IFS= read -r rc < "$tmpdir/step16-exit" || rc=0
    fi
    exit "$rc"
    ;;
  "slack issue-announce")
    status=skipped
    if [ -f "$tmpdir/slack-status" ]; then
      IFS= read -r status < "$tmpdir/slack-status" || status=skipped
    fi
    printf 'STATUS=%s\n' "$status"
    exit 0
    ;;
  "final-report write")
    mode=success
    if [ -f "$tmpdir/step17-mode" ]; then
      IFS= read -r mode < "$tmpdir/step17-mode" || mode=success
    fi
    case "$mode" in
      success)
        printf '# Summary\n' > "$tmpdir/summary-final.md"
        printf 'STATUS=ok\n'
        exit 0
        ;;
      success-no-newline)
        printf '# Summary' > "$tmpdir/summary-final.md"
        printf 'STATUS=ok\n'
        exit 0
        ;;
      fail-upsert)
        printf 'fresh body\n' > "$tmpdir/summary-final.md"
        printf 'tracking upsert failed\n'
        exit 7
        ;;
      fail-empty)
        : > "$tmpdir/summary-final.md"
        printf 'render failed before body\n'
        exit 7
        ;;
      fail-stale)
        printf 'render failed before refresh\n'
        exit 7
        ;;
      *)
        printf 'unknown step17 mode\n'
        exit 8
        ;;
    esac
    ;;
  "run-log append-failure")
    shift 2
    log=
    site=
    tool=
    exit_code=
    category=
    output_file=
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --log) shift; log=$1 ;;
        --site) shift; site=$1 ;;
        --tool) shift; tool=$1 ;;
        --exit-code) shift; exit_code=$1 ;;
        --category) shift; category=$1 ;;
        --output-file) shift; output_file=$1 ;;
      esac
      shift
    done
    {
      printf 'CATEGORY=%s\n' "$category"
      printf 'SITE=%s\n' "$site"
      printf 'TOOL=%s\n' "$tool"
      printf 'EXIT=%s\n' "$exit_code"
      if [ -f "$output_file" ]; then
        while IFS= read -r line; do
          printf 'OUTPUT=%s\n' "$line"
        done < "$output_file"
      fi
    } >> "$log"
    exit 0
    ;;
  *)
    printf 'unexpected closeout child: %s\n' "$*" >&2
    exit 64
    ;;
esac
