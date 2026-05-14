## Goal
Fix safety-net per-section record splitting and Step-11-aware dedup in implement-finalize.sh

## Implementation Plan
## Implementation Plan

Fix two bugs in scripts/implement-finalize.sh:flush_execution_issues_safety_net.

### Bug 1: Hardcoded "Tool Failures" category

Rename write_execution_issues_record → write_execution_issues_records and change it to:
- Parse ### header lines from execution-issues.md
- For each section, write body to a temp file, call jq -Rs to emit a record with the actual category
- If no ### headers found, fall back to one "Tool Failures" record
- python3 fallback: single record, no splitting

### Bug 2: Unreliable dedup grep

Change: grep -Fq "$sha" "$batch_path"
To: grep -Fq '"source_sha256":"'"$sha"'"' "$batch_path"

### Files to modify

1. scripts/implement-finalize.sh — rename function, add per-section loop, fix grep (~30 LOC)
2. scripts/test-implement-finalize.sh — add 4 regression tests
3. scripts/implement-finalize.md — update function name reference

### Testing strategy

Run: make test-implement-finalize
Verify tests pass for multi-section splitting, dedup behaviors.

## Test plan
(no test plan section in plan-file)
