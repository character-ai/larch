## Goal
Add regression harness for cache-key-runtime-audit.py covering BASELINE, EXPECTED-GROWTH, and CACHE-INVALIDATING cases

## Implementation Plan

Goal: Add a shell regression harness for scripts/cache-key-runtime-audit.py with BASELINE, EXPECTED-GROWTH, and CACHE-INVALIDATING test cases, wire it into Makefile shard 7 and .PHONY list, and add a sibling .md doc.

### Files to create/modify

1. **scripts/test-cache-key-runtime-audit.sh** (new) — regression harness
2. **scripts/test-cache-key-runtime-audit.md** (new) — sibling doc stub
3. **Makefile** (modify) — add to .PHONY, shard 7, and standalone target

### Approach

**scripts/test-cache-key-runtime-audit.sh**:
- `set -euo pipefail`, `LC_ALL=C`
- `pass()`/`fail()` helpers with PASS/FAIL counters
- `mktemp -d` temp dir + `trap cleanup EXIT`
- Three fixture log roots, each with one `run1/session-transcript.jsonl`:
  1. BASELINE: sys1→usr1→ast1 (single assistant turn)
  2. EXPECTED-GROWTH: sys1→usr1→ast1→usr2→ast2, where ast2 chains through same sys1+usr1 prefix
  3. CACHE-INVALIDATING: sys1→usr1→ast1 and sys1→usr3→ast2, where usr1 and usr3 have different content
- Each fixture invokes `python3 scripts/cache-key-runtime-audit.py --log-root <dir> --runs 1`
- Error case: non-existent log root → assert exit code 2
- Final: exit 1 if FAIL > 0, else `printf 'PASS: cache-key-runtime-audit harness (%d tests)\n' "$PASS"`

**JSONL fixture entries** per case:
- BASELINE: `{"type":"system","uuid":"sys1","parentUuid":null,"subtype":"init","message":{"content":"system prompt"}}` + user + single assistant
- EXPECTED-GROWTH: 5 entries where second assistant's chain produces same prefix as first
- CACHE-INVALIDATING: 5 entries where ast2 parents sys1→usr3 (different content from usr1), triggering CACHE-INVALIDATING

**scripts/test-cache-key-runtime-audit.md** (stub):
- Points to `scripts/cache-key-runtime-audit.md` as the primary contract owner
- Lists purpose, primary callers (make test-cache-key-runtime-audit, make test-harnesses-7), edit-in-sync note

**Makefile changes**:
- Add `test-cache-key-runtime-audit` to the .PHONY line alongside `test-cache-key-discipline`
- Add `test-cache-key-runtime-audit` to `test-harnesses-7` shard
- Add standalone target: `test-cache-key-runtime-audit:\n\tbash scripts/test-cache-key-runtime-audit.sh`

### Testing strategy
- `make test-cache-key-runtime-audit` → PASS
- `make test-harnesses-7` must continue to pass
- Verify BASELINE/EXPECTED-GROWTH/CACHE-INVALIDATING classification logic by reading cache-key-runtime-audit.py

## Test plan
(no test plan section in plan-file)
