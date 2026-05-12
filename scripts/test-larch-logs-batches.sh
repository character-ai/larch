#!/usr/bin/env bash
# test-larch-logs-batches.sh — batch table consistency checks.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# shellcheck source=scripts/larch-log-batches.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/larch-log-batches.sh"

expected='plan-goals-test
plan-review-tally
code-review-tally
review-findings-full
diagrams
version-bump-reasoning
oos-issues
run-statistics
token-report
timing-report
execution-issues
session-transcript'

actual="$(larch_log_batch_list)"
[ "$actual" = "$expected" ] || {
    echo "FAIL: batch list drift" >&2
    printf 'expected:\n%s\nactual:\n%s\n' "$expected" "$actual" >&2
    exit 1
}

for slug in $actual; do
    ext="$(larch_log_batch_extension "$slug")"
    mode="$(larch_log_batch_mode "$slug")"
    sanitizer="$(larch_log_batch_sanitizer "$slug")"
    case "$ext" in .md|.ndjson|.json|.jsonl) ;; *) echo "FAIL: invalid extension for $slug: $ext" >&2; exit 1 ;; esac
    case "$mode" in replace|append) ;; *) echo "FAIL: invalid mode for $slug: $mode" >&2; exit 1 ;; esac
    case "$sanitizer" in none|mermaid) ;; *) echo "FAIL: invalid sanitizer for $slug: $sanitizer" >&2; exit 1 ;; esac
done

[ "$(larch_log_batch_extension diagrams)" = ".md" ]
[ "$(larch_log_batch_mode token-report)" = "replace" ]
[ "$(larch_log_batch_extension token-report)" = ".md" ]
[ "$(larch_log_batch_mode timing-report)" = "replace" ]
[ "$(larch_log_batch_extension timing-report)" = ".md" ]
[ "$(larch_log_batch_sanitizer diagrams)" = "mermaid" ]

echo "All assertions passed."
