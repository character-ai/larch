#!/usr/bin/env bash
# larch-log-batches.sh — canonical larch-log batch table.

set -euo pipefail

LARCH_LOG_BATCHES="
plan-goals-test .md replace plan-goals
plan-review-tally .ndjson append none
code-review-tally .ndjson append none
review-findings-full .ndjson append none
review-context .md replace none
review-findings .ndjson append none
review-panel-manifest .ndjson replace none
review-round-summary .md replace none
review-tally .md replace none
version-bump-reasoning .md replace none
oos-issues .ndjson append none
run-statistics .md replace none
token-report .md replace none
timing-report .md replace none
execution-issues .ndjson append none
session-transcript .jsonl replace none
"

larch_log_batch_info() {
    local slug="$1"
    printf '%s\n' "$LARCH_LOG_BATCHES" | awk -v slug="$slug" '
        NF == 4 && $1 == slug { print $2 " " $3 " " $4; found = 1 }
        END { if (!found) exit 1 }
    '
}

larch_log_batch_extension() {
    larch_log_batch_info "$1" | awk '{ print $1 }'
}

larch_log_batch_mode() {
    larch_log_batch_info "$1" | awk '{ print $2 }'
}

larch_log_batch_sanitizer() {
    larch_log_batch_info "$1" | awk '{ print $3 }'
}

larch_log_batch_list() {
    printf '%s\n' "$LARCH_LOG_BATCHES" | awk 'NF == 4 { print $1 }'
}
