## Goal
Build a runtime cache-key audit script for larch-logs/implement/ session transcripts

## Implementation Plan

### Goal
Build scripts/cache-key-runtime-audit.py to analyze session-transcript.jsonl files from larch-logs/implement/ runs. Detect CACHE-INVALIDATING prompt content that shouldn't change between consecutive API calls. Add a Makefile target and run the audit against ~10 post-#1438 runs.

### What gets built
1. `scripts/cache-key-runtime-audit.py` — the analyzer
2. Makefile target `audit-cache-keys-runtime RUNS=10`
3. Apply fixes for any CACHE-INVALIDATING findings discovered

### Script design (cache-key-runtime-audit.py)

Input: N most recent larch-logs/implement/<RUN_ID>/session-transcript.jsonl files

Algorithm per run:
1. Parse all valid NDJSON entries from session-transcript.jsonl
2. Build uuid→entry map; deduplicate `assistant` entries by requestId
3. Build conversation tree (uuid → parentUuid chain)
4. For each unique assistant entry (in conversation order):
   a. Follow parentUuid chain to root
   b. Collect "stable prefix" = all `system` entries + `user` entries with isMeta=True
   c. Compute SHA256 of concatenated stable prefix content
   d. Compare hash to previous turn's hash
5. Classify each turn:
   - First turn: baseline (no comparison)
   - Hash unchanged: EXPECTED-GROWTH (conversation tail grows, prefix stable) 
   - Hash changed, new isMeta entry added: EXPECTED-GROWTH (new skill loaded)
   - Hash changed, same isMeta entries but content differs: CACHE-INVALIDATING
6. For CACHE-INVALIDATING turns: compute difflib unified diff of prefix content, identify changed lines

Output: structured markdown report per run with:
- Summary: total turns, CACHE-INVALIDATING count, cache efficiency per turn
- Per-finding: turn number, diff of changed content, source pattern

### Makefile target
```makefile
RUNS ?= 10
audit-cache-keys-runtime:
	python3 scripts/cache-key-runtime-audit.py --runs "$(RUNS)" --log-root larch-logs/implement
```

### Running the audit
After building the script:
1. Run `make audit-cache-keys-runtime RUNS=10` against the 10 most recent runs
2. Review the report for CACHE-INVALIDATING findings
3. Apply fixes (same move/stabilize/remove pattern as static audit)

### Files to create
- `scripts/cache-key-runtime-audit.py` (new)
- Makefile target `audit-cache-keys-runtime` (add to Makefile + .PHONY)

### Edge cases
- Run has no session-transcript.jsonl: skip with warning
- Run has zero assistant entries: skip
- parentUuid chain has cycles: guard with visited set
- isMeta content is a list of content blocks vs a string: handle both
- Very large diffs: truncate to 2000 chars in report

## Test plan
(no test plan section in plan-file)
