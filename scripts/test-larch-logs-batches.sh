#!/usr/bin/env bash
# test-larch-logs-batches.sh — batch table consistency checks.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# shellcheck source=scripts/larch-log-batches.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/larch-log-batches.sh"
# shellcheck source=scripts/lib-larch-log.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-larch-log.sh"

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
    case "$sanitizer" in none|mermaid|plan-goals|json-lines) ;; *) echo "FAIL: invalid sanitizer for $slug: $sanitizer" >&2; exit 1 ;; esac
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

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/larch-log-batches-test.XXXXXX")"
trap 'rm -rf "$tmpdir"' EXIT

assert_json_lines_accepts() {
    local label="$1"
    local file="$2"
    if ! larch_log_validate_batch_payload plan-review-tally "$file" >/dev/null; then
        echo "FAIL: expected json-lines validator to accept $label" >&2
        exit 1
    fi
}

assert_json_lines_rejects() {
    local label="$1"
    local file="$2"
    local output rc
    set +e
    output="$(bash -c '
        set -euo pipefail
        source "$1/lib-larch-log.sh"
        larch_log_validate_batch_payload plan-review-tally "$2"
    ' _ "$SCRIPT_DIR" "$file" 2>&1)"
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
        echo "FAIL: expected json-lines validator to reject $label" >&2
        exit 1
    fi
    case "$output" in
        *"ERROR=json-lines sanitizer rejected plan-review-tally: invalid JSON line"*) ;;
        *)
            echo "FAIL: expected ERROR= line for rejected $label" >&2
            printf '%s\n' "$output" >&2
            exit 1
            ;;
    esac
}

valid_single="$tmpdir/valid-single.ndjson"
invalid_text="$tmpdir/invalid-text.ndjson"
empty_file="$tmpdir/empty.ndjson"
valid_multi="$tmpdir/valid-multi.ndjson"
mixed="$tmpdir/mixed.ndjson"

printf '{"schema_version":1,"body":"ok"}\n' > "$valid_single"
printf 'plain text\n' > "$invalid_text"
: > "$empty_file"
{
    printf '{"schema_version":1,"body":"one"}\n'
    printf '{"schema_version":1,"body":"two"}\n'
} > "$valid_multi"
{
    printf '{"schema_version":1,"body":"one"}\n'
    printf 'plain text\n'
} > "$mixed"

assert_json_lines_accepts "single JSON line" "$valid_single"
assert_json_lines_rejects "plain text" "$invalid_text"
assert_json_lines_accepts "empty file" "$empty_file"
assert_json_lines_accepts "multi-line NDJSON" "$valid_multi"
assert_json_lines_rejects "mixed JSON and text" "$mixed"

echo "All assertions passed."
