## Goal
Rebalance CI shards by splitting test-dispatch-code-voters.sh into 6 sections

## Implementation Plan

Goal: Split test-dispatch-code-voters.sh 11 scenarios into 6 sections to keep all CI shards ≤40s.

### File 1 — scripts/test-dispatch-code-voters.sh

1a. Update docstring (lines 7-11): change from "5 scenarios in 2 groups" to 11 scenarios in 6 groups, listing all 6 section names.

1b. Gate the 6 ungated retry scenarios in 4 new section_runs blocks:
- Lines 218-240 (retry_success_claude) + lines 242-267 (retry_fail_claude) → wrap in `if section_runs retry-claude; then ... fi  # end section: retry-claude`
- Lines 269-288 (retry_success_codex) → wrap in `if section_runs retry-codex-success; then ... fi  # end section: retry-codex-success`
- Lines 289-307 (retry_success_cursor) → wrap in `if section_runs retry-cursor; then ... fi  # end section: retry-cursor`
- Lines 309-345 (retry_fail_codex + retry_fail_fallback) → wrap in `if section_runs retry-codex-fail-and-fallback; then ... fi  # end section: retry-codex-fail-and-fallback`

1c. Do not touch setup code (lines 1-141) or the `echo "PASS: ..."` at line 346.

### File 2 — Makefile

2a. Add 4 new shard targets to .PHONY line 4: `test-harnesses-15 test-harnesses-16 test-harnesses-17 test-harnesses-18`
2b. Add 4 new dispatch targets to .PHONY: `test-dispatch-code-voters-retry-claude test-dispatch-code-voters-retry-codex-success test-dispatch-code-voters-retry-cursor test-dispatch-code-voters-retry-codex-fail-and-fallback`
2c. Update test-harnesses umbrella line 32 to include shards 15-18.
2d. Move test-rebase-push-force-lease and test-ballot-parse from shard 9 to shard 12 (append).
2e. Update shard 9 to only run test-dispatch-code-voters-edge (no extra tests).
2f. Add new shard recipe lines for 15, 16, 17, 18.
2g. Add 4 new dispatch target recipe lines following existing happy/edge pattern.

### File 3 — .github/workflows/ci.yaml

3a. Update shard array at line 168: from [1..14] to [1..18].
3b. Update label at line 204: "of 14" → "of 18".

### File 4 — scripts/test-harness-shards-coverage.sh

Read to verify no hardcoded 14 — it dynamically discovers from Makefile, so no change needed.

### File 5 — Sibling .md docs

5a. Update scripts/test-dispatch-code-voters.md to describe 6-section split.
5b. Grep for "14 shard", "of 14", "14 test-harnesses" in docs/, README.md, SECURITY.md, .github/workflows/, skills/**. Update matches.


## Test plan

- `bash scripts/test-dispatch-code-voters.sh` (no --section) passes
- `bash scripts/test-dispatch-code-voters.sh --section <each>` passes for all 6 sections
- `bash scripts/test-harness-shards-coverage.sh` passes
- `bash scripts/test-harness-shards-coverage.sh --self-test` passes
