## Goal
Fix execution-issues safety-net dedup to use normalized per-section sha so whitespace-divergent duplicates are correctly identified

## Implementation Plan
## Implementation Plan

### Goal
Fix the execution-issues safety-net dedup in `scripts/implement-finalize.sh` so that whitespace-divergent duplicates (same failure, different leading/trailing whitespace or missing `### Header`) are correctly identified as duplicates and not double-emitted.

### Root Cause
`flush_execution_issues_safety_net` computes sha256 of the whole `execution-issues.md` file. If the file grows between Step 11's flush and Step 18's safety-net (e.g., a Warnings section is appended), the file sha changes. The batch dedup check `grep -Fq '"source_sha256":"$sha"'` then misses Step 11's record, causing `write_execution_issues_records` to re-emit all sections including Tool Failures (already written at Step 11).

### Changes

1. **`scripts/implement-finalize.sh`**:
   a. Add `sha256_stream()` — sha256 of stdin (wraps `shasum -a 256` or `sha256sum`).
   b. Add `normalize_body_for_hash()` — reads stdin, strips leading `### Category` header line (awk: skip when NR==1 && /^### /), strips leading and trailing blank lines, outputs normalized content. Preserves internal content verbatim (code fences safe).
   c. Change `write_execution_issues_records` signature: add optional 4th arg `batch_path=${4:-}`.
   d. In the jq path, for each section body before emitting:
      - Compute `norm_sha=$(normalize_body_for_hash < "$body_file" | sha256_stream 2>/dev/null || true)`
      - If `norm_sha` non-empty AND `batch_path` provided AND batch file exists: check `grep -Fq '"source_sha256":"$norm_sha"'` → skip if found
      - Use `norm_sha` (fallback `$sha`) as `source_sha256` in emitted record
   e. In `flush_execution_issues_safety_net`:
      - Pass `$batch_path` as 4th arg to `write_execution_issues_records`
      - After `write_execution_issues_records` returns, if `$record_file` is empty: update sentinel and return (all sections deduped, nothing to append)

2. **`scripts/implement-finalize.md`** — update the Behavior Mapping bullet that describes the safety-net:
   - Change "its SHA-256 is not already recorded in `.execution-issues-flushed.sha` or the `execution-issues.ndjson` batch (checked via a `"source_sha256":"<sha>"` field-targeted grep to avoid false dedup against Q/A per-entry records that lack that field)" → "the safety-net uses per-section normalized-sha dedup: for each section body, strip the leading `### Category` header and leading/trailing blank lines, compute sha256 of the result, and check if `"source_sha256":"<norm-sha>"` already exists in the batch"

3. **`skills/implement/SKILL.md`** — update line 1564 (Step 11 contract):
   - After "Include `source_sha256` in the record payload" add: "The sha is computed over the normalized body — strip the leading `### Category` header line and leading/trailing blank lines, then sha256. This matches `normalize_body_for_hash` in `implement-finalize.sh` so the safety-net's per-section dedup correctly identifies duplicate sections."
   - Update "write the SHA-256 of the exact markdown source" → keep as-is (sentinel still uses whole-file sha for the fast-path optimization)

4. **`scripts/test-implement-finalize.sh`** — add whitespace-divergent dedup test:
   - Compute normalized sha of a section body (e.g., "- apply-bump.sh failed")
   - Pre-populate `execution-issues.ndjson` batch with a Step 11 record using that normalized sha
   - Write `execution-issues.md` with a differently-whitespaced version of the same body (leading blank line, trailing blank line)
   - Run teardown (which calls flush_execution_issues_safety_net)
   - Assert: the safety-net does NOT emit a duplicate record for that section

### Testing
- Existing tests still pass (run `scripts/test-implement-finalize.sh`)
- New test verifies whitespace-divergent dedup works
- `/relevant-checks` passes (pre-commit + agent-lint)

## Test plan
(no test plan section in plan-file)
