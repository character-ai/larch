## Goal
Fix -R flag regression in audit-preflight.sh and jstr() truncation in audit-scan-run.sh

## Implementation Plan
Fix two regressions in audit-runs scripts from PR #2495.


### Fix 1 — audit-preflight.sh: unsupported -R flag on gh repo view

**Root cause**: `gh repo view` is positional-only; `-R`/`--repo` is not a valid flag.

**Files to change**:
- `.claude/skills/audit-runs/scripts/audit-preflight.sh`
  - Line 63: `gh repo view -R "$REPO" --json url --jq '.url'` → `gh repo view "$REPO" --json url --jq '.url'`
  - Line 85: error message `expected clone to match gh repo view -R %s` → `expected clone to match gh repo view %s`
- `.claude/skills/audit-runs/scripts/audit-preflight.md`
  - Line 17: `gh repo view -R REPO --json url` → `gh repo view REPO --json url`

### Fix 2 — audit-scan-run.sh: jstr() strips first/last char

**Root cause**: `jq -nj --arg s "$1" '$s'` emits raw (unquoted) string, but
the `${_j:1:${#_j}-2}` slice was written assuming jq would emit a quoted
JSON string like `"hello"`. Fix: use `$s | @json` so jq emits the quoted
form `"hello"`, and the slice correctly strips the surrounding quotes.

**File to change**:
- `.claude/skills/audit-runs/scripts/audit-scan-run.sh`
  - Line 67: `jq -nj --arg s "$1" '$s'` → `jq -nj --arg s "$1" '$s | @json'`

### Fix 3 — test-audit-runs.sh: add regression coverage

**Tests to add/modify**:
- Tighten Test 44's `gh` stub to reject `-R` on `repo view`
- Add Test 44b: run preflight with strict stub, assert PREFLIGHT_OK=true
- Add Test 49: jstr() round-trip fixture asserting identity for representative strings


## Test plan
Run `bash .claude/skills/audit-runs/scripts/test-audit-runs.sh` — all existing tests
plus new Test 44b and Test 49 must pass, and would FAIL on the pre-fix script versions.
