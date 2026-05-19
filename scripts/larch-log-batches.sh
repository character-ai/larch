#!/usr/bin/env bash
# larch-log-batches.sh — canonical larch-log batch table.

set -euo pipefail

LARCH_LOG_BATCHES="
plan-goals-test .md replace plan-goals
parent-issue .md replace none
pre-review-head .txt replace none
pre-review-untracked .txt replace none
codex-impl-transcript .txt replace none
codex-impl-transcript-meta .txt.meta replace none
codex-impl-transcript-prompt .txt replace none
codex-commit-message .txt replace none
codex-impl-manifest-raw .json replace none
plan-review-tally .json replace json-object
code-review-tally .json replace json-object
review-findings-full .md replace none
review-context .md replace none
review-findings .ndjson append json-lines
review-panel-manifest .ndjson replace none
review-round-summary .md replace none
review-scout-manifest .json replace json-object
review-tally .md replace none
version-bump-reasoning .md replace none
oos-issues .ndjson append json-lines
run-statistics .md replace none
token-report .json replace none
timing-report .json replace none
execution-issues .ndjson append json-lines
session-transcript .md replace none
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
