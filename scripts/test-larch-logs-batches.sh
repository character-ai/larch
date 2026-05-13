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
review-context
review-findings
review-panel-manifest
review-round-summary
review-tally
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
    case "$sanitizer" in none|mermaid|plan-goals) ;; *) echo "FAIL: invalid sanitizer for $slug: $sanitizer" >&2; exit 1 ;; esac
done

[ "$(larch_log_batch_mode token-report)" = "replace" ]
[ "$(larch_log_batch_extension token-report)" = ".md" ]
[ "$(larch_log_batch_mode timing-report)" = "replace" ]
[ "$(larch_log_batch_extension timing-report)" = ".md" ]
[ "$(larch_log_batch_mode run-statistics)" = "replace" ]
[ "$(larch_log_batch_extension run-statistics)" = ".md" ]
[ "$(larch_log_batch_sanitizer plan-goals-test)" = "plan-goals" ]

tmp="$(mktemp -d "${TMPDIR:-/tmp}/test-larch-log-batches.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

pointer_payload="$tmp/pointer-plan-goals.md"
cat > "$pointer_payload" <<'EOF'
## Goal
Prevent placeholder plans.

## Implementation Plan
See plan.txt

## Test plan
Run the larch-log batch tests.
EOF

valid_payload="$tmp/valid-plan-goals.md"
cat > "$valid_payload" <<'EOF'
## Goal
Prevent placeholder plans.

## Implementation Plan
## Implementation Plan
Add a dedicated composer for the plan-goals-test batch, wire the batch table to
the plan-goals sanitizer, and update the regression harnesses so sectioned
payloads are required before larch-log writes can publish the artifact.

## Test plan
Run scripts/test-compose-plan-goals-test.sh and scripts/test-larch-logs-batches.sh.
EOF

set +e
LARCH_LOG_ROOT="$tmp/logs" "$SCRIPT_DIR/larch-log.sh" write --skill implement --run-id pointer --batch plan-goals-test --input-file "$pointer_payload" >/dev/null 2>&1
pointer_rc=$?
set -e
[ "$pointer_rc" -ne 0 ] || { echo "FAIL: pointer-only plan-goals payload should be rejected" >&2; exit 1; }

LARCH_LOG_ROOT="$tmp/logs" "$SCRIPT_DIR/larch-log.sh" write --skill implement --run-id valid --batch plan-goals-test --input-file "$valid_payload" >/dev/null

echo "All assertions passed."
