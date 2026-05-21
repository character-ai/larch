## Goal
Add character allowlist validation on relative_path before glob expansion in verify-run-log-completeness.sh

## Implementation Plan

### Goal
Harden `scripts/verify-run-log-completeness.sh` against unexpected glob expansion by adding a character allowlist validation on `relative_path` values read from `docs/run-logs-required-files.tsv`.

### Files to Modify
1. `scripts/verify-run-log-completeness.sh` — add two changes:
   a. Support `LARCH_VERIFY_MANIFEST` env override for testability (line 9)
   b. Add allowlist validation after the `..` check (after line 119)
2. `scripts/verify-run-log-completeness.md` — document `LARCH_VERIFY_MANIFEST`
3. `scripts/test-verify-run-log-completeness.sh` — add test for invalid characters

### Changes

**scripts/verify-run-log-completeness.sh:**
- Change line 9 from `MANIFEST="$REPO_ROOT/docs/run-logs-required-files.tsv"` to
  `MANIFEST="${LARCH_VERIFY_MANIFEST:-$REPO_ROOT/docs/run-logs-required-files.tsv}"`
- After the existing `*..*)` case block (after line 119), add:
  ```bash
  if ! printf '%s' "$relative_path" | LC_ALL=C grep -qE '^[A-Za-z0-9_./*-]+$'; then
      printf 'verify-run-log-completeness.sh: invalid characters in relative_path: %s\n' "$relative_path" >&2
      exit 1
  fi
  ```

**scripts/test-verify-run-log-completeness.sh:**
- Add test 14: create a temp manifest with a relative_path containing a space;
  set LARCH_VERIFY_MANIFEST to it; assert verifier exits with "invalid characters" error.


## Test plan
- `make test-verify-run-log-completeness` → all tests pass including the new one
- `/relevant-checks` (pre-commit on modified files + agent-lint) → clean
