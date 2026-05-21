## Goal
Add NS_RETRY_REASON token to ns-retry .meta files and expose reasons breakdown in audit scan

## Implementation Plan

### Goal
Log NOT_SUBSTANTIVE classification reason as NS_RETRY_REASON=<token> in *-ns-retry.txt.meta files
so audits can bin by cause.

### Files to modify

1. **scripts/collect-agent-results.sh**
   - Add `derive_ns_retry_reason()` helper mapping VAL_EXIT + ns_mode → token
   - Section 3.5: append `|NS_RETRY_REASON=<token>` to NOT_SUBSTANTIVE RESULTS entry
   - Section 3.6: append `|NS_RETRY_REASON=<token>` to NOT_SUBSTANTIVE RESULTS entry
   - Section 3.7 post-wait loop: extract reason from RESULTS[IDX], append to NS_RETRY_OUTPUT.meta
   
   Token mapping:
   - Substantive mode: VAL_EXIT=2 → NO_ISSUES_FOUND_TOO_THIN; 3 → NO_ISSUES_FOUND_TOO_THIN; 4 → OUTPUT_EMPTY; else → UNKNOWN
   - Structured mode: VAL_EXIT=5 → JSON_PARSE_FAIL; else → UNKNOWN

2. **.claude/skills/audit-runs/scripts/audit-scan-run.sh** `scan_ns_retry_sidecars()`
   - Read each *-ns-retry*.txt.meta, parse NS_RETRY_REASON= line
   - Build per-reason count map; emit reasons:{...} alongside count: in JSON output

3. **scripts/test-collect-agent-results.sh**
   - Add C_NS_REASON assertion: after C_NS_RETRY run, check NS_RETRY_REASON=NO_ISSUES_FOUND_TOO_THIN in the ns-retry .meta

4. **scripts/collect-agent-results.md** (sibling doc)
   - Document NS_RETRY_REASON= field in the .meta contract section

5. **.claude/skills/audit-runs/scripts/audit-scan-run.md** (sibling doc)
   - Document reasons:{} field in ns-retry-sidecars scan output

### Approach
- The derive_ns_retry_reason() function maps validator exit codes to vocabulary tokens.
- The NS_RETRY_REASON is stored in the pipe-delimited RESULTS array entry, then written
  to disk via printf >> NS_RETRY_OUTPUT.meta in the post-wait loop.
- The audit scan uses awk to parse the meta files for the NS_RETRY_REASON= line.


## Test plan
- Run make test / scripts/test-collect-agent-results.sh to verify new assertion passes
- Run relevant-checks to validate agent-lint and lint-bash32 compliance
