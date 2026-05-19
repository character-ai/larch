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
parent-issue
pre-review-head
pre-review-untracked
codex-impl-transcript
codex-impl-transcript-meta
codex-impl-transcript-prompt
codex-commit-message
codex-impl-manifest-raw
plan-review-tally
code-review-tally
review-findings-full
review-context
review-findings
review-panel-manifest
review-round-summary
review-scout-manifest
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
    case "$ext" in .md|.txt|.txt.meta|.ndjson|.json|.jsonl) ;; *) echo "FAIL: invalid extension for $slug: $ext" >&2; exit 1 ;; esac
    case "$mode" in replace|append) ;; *) echo "FAIL: invalid mode for $slug: $mode" >&2; exit 1 ;; esac
    case "$sanitizer" in none|mermaid|plan-goals|json-lines|json-object) ;; *) echo "FAIL: invalid sanitizer for $slug: $sanitizer" >&2; exit 1 ;; esac
done

[ "$(larch_log_batch_mode token-report)" = "replace" ]
[ "$(larch_log_batch_extension token-report)" = ".json" ]
[ "$(larch_log_batch_mode timing-report)" = "replace" ]
[ "$(larch_log_batch_extension timing-report)" = ".json" ]
[ "$(larch_log_batch_mode run-statistics)" = "replace" ]
[ "$(larch_log_batch_extension run-statistics)" = ".md" ]
[ "$(larch_log_batch_sanitizer plan-goals-test)" = "plan-goals" ]
[ "$(larch_log_batch_mode parent-issue)" = "replace" ]
[ "$(larch_log_batch_extension parent-issue)" = ".md" ]
[ "$(larch_log_batch_mode pre-review-head)" = "replace" ]
[ "$(larch_log_batch_extension pre-review-head)" = ".txt" ]
[ "$(larch_log_batch_mode pre-review-untracked)" = "replace" ]
[ "$(larch_log_batch_extension pre-review-untracked)" = ".txt" ]
[ "$(larch_log_batch_mode codex-impl-transcript)" = "replace" ]
[ "$(larch_log_batch_extension codex-impl-transcript)" = ".txt" ]
[ "$(larch_log_batch_mode codex-impl-transcript-meta)" = "replace" ]
[ "$(larch_log_batch_extension codex-impl-transcript-meta)" = ".txt.meta" ]
[ "$(larch_log_batch_mode codex-impl-transcript-prompt)" = "replace" ]
[ "$(larch_log_batch_extension codex-impl-transcript-prompt)" = ".txt" ]
[ "$(larch_log_batch_mode codex-commit-message)" = "replace" ]
[ "$(larch_log_batch_extension codex-commit-message)" = ".txt" ]
[ "$(larch_log_batch_mode codex-impl-manifest-raw)" = "replace" ]
[ "$(larch_log_batch_extension codex-impl-manifest-raw)" = ".json" ]
[ "$(larch_log_batch_mode plan-review-tally)" = "replace" ]
[ "$(larch_log_batch_extension plan-review-tally)" = ".json" ]
[ "$(larch_log_batch_sanitizer plan-review-tally)" = "json-object" ]
[ "$(larch_log_batch_mode code-review-tally)" = "replace" ]
[ "$(larch_log_batch_extension code-review-tally)" = ".json" ]
[ "$(larch_log_batch_sanitizer code-review-tally)" = "json-object" ]
[ "$(larch_log_batch_mode review-findings-full)" = "replace" ]
[ "$(larch_log_batch_extension review-findings-full)" = ".jsonl" ]
[ "$(larch_log_batch_sanitizer review-findings-full)" = "none" ]

tmp="$(mktemp -d "${TMPDIR:-/tmp}/test-larch-log-batches.XXXXXX")"
tmpdir=""
trap 'rm -rf "$tmp" "${tmpdir:-}"' EXIT

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

LARCH_LOG_BATCHES="$LARCH_LOG_BATCHES
test-json-lines .ndjson append json-lines
"

assert_json_lines_accepts() {
    local label="$1"
    local file="$2"
    if ! larch_log_validate_batch_payload test-json-lines "$file" >/dev/null; then
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
        LARCH_LOG_BATCHES="$LARCH_LOG_BATCHES
test-json-lines .ndjson append json-lines
"
        larch_log_validate_batch_payload test-json-lines "$2"
    ' _ "$SCRIPT_DIR" "$file" 2>&1)"
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
        echo "FAIL: expected json-lines validator to reject $label" >&2
        exit 1
    fi
    case "$output" in
        *"ERROR=json-lines sanitizer rejected test-json-lines: invalid JSON line"*) ;;
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
whitespace_only="$tmpdir/whitespace-only.ndjson"

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
printf '   \n\t\n' > "$whitespace_only"

assert_json_lines_accepts "single JSON line" "$valid_single"
assert_json_lines_rejects "plain text" "$invalid_text"
assert_json_lines_accepts "empty file" "$empty_file"
assert_json_lines_accepts "multi-line NDJSON" "$valid_multi"
assert_json_lines_rejects "mixed JSON and text" "$mixed"
assert_json_lines_accepts "whitespace-only lines" "$whitespace_only"

assert_json_object_accepts() {
    local label="$1"
    local file="$2"
    if ! larch_log_validate_batch_payload plan-review-tally "$file" >/dev/null; then
        echo "FAIL: expected json-object validator to accept $label" >&2
        exit 1
    fi
}

assert_json_object_rejects() {
    local label="$1"
    local file="$2"
    local expected="$3"
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
        echo "FAIL: expected json-object validator to reject $label" >&2
        exit 1
    fi
    case "$output" in
        *"$expected"*) ;;
        *)
            echo "FAIL: expected ERROR= line for rejected $label" >&2
            printf '%s\n' "$output" >&2
            exit 1
            ;;
    esac
}

valid_object="$tmpdir/valid-object.json"
invalid_object_text="$tmpdir/invalid-object-text.json"
array_object="$tmpdir/array.json"
primitive_object="$tmpdir/primitive.json"
multi_object="$tmpdir/multi-object.json"

printf '{"schema_version":1,"body":"ok"}\n' > "$valid_object"
printf 'plain text\n' > "$invalid_object_text"
printf '[{"schema_version":1}]\n' > "$array_object"
printf '"text"\n' > "$primitive_object"
{
    printf '{"schema_version":1,"body":"one"}\n'
    printf '{"schema_version":1,"body":"two"}\n'
} > "$multi_object"

_json_obj_err="ERROR=json-object sanitizer rejected plan-review-tally: expected exactly one top-level JSON object"
assert_json_object_accepts "single JSON object" "$valid_object"
assert_json_object_rejects "plain text" "$invalid_object_text" "$_json_obj_err"
assert_json_object_rejects "array" "$array_object" "$_json_obj_err"
assert_json_object_rejects "primitive" "$primitive_object" "$_json_obj_err"
assert_json_object_rejects "multi-object stream" "$multi_object" "$_json_obj_err"

echo "All assertions passed."
