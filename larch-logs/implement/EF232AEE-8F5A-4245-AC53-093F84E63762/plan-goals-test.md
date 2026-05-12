## Goal
Add harness tests asserting --workflow SIMPLE/HARD selects the correct --timeout for the launcher call in step2-implement.sh.

## Goal
Add harness tests asserting --workflow SIMPLE/HARD selects the correct --timeout for the launcher call in step2-implement.sh.

## Implementation Plan

### Files to modify
1. `skills/implement/scripts/test-step2-dispatch.sh` — add Tests 17a and 17b after the existing Test 16 block (before the Summary section)
2. `skills/implement/scripts/test-step2-dispatch.md` — add entry 17 to the Coverage list

### Approach
- Add a shared stub codex binary (STUB17) that writes a status=bailed manifest (same pattern as Test 12's STUB_CODEX)
- Test 17a: run dispatcher with --coder codex --workflow SIMPLE, then check that $TMP17A/codex-impl-transcript.txt.meta has TIMEOUT=3600
- Test 17b: run dispatcher with --coder codex --workflow HARD, then check TIMEOUT=7200
- Use same env setup as tests 12–16: LARCH_CODEX_MODEL=stub-codex-model, RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05, STEP2_MANIFEST_PATH, run from $REPO_ROOT
- Update the header comment block (lines 31-36 area) in test-step2-dispatch.sh to add the two new test descriptions
- Update test-step2-dispatch.md Coverage list with entry 17

### Testing strategy
Run `make test-step2-dispatch` (or `bash skills/implement/scripts/test-step2-dispatch.sh`) to verify the new tests produce PASS output.

## Test plan
Run `make test-step2-dispatch` or `bash skills/implement/scripts/test-step2-dispatch.sh`.
