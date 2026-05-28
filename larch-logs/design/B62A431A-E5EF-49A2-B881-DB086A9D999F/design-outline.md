## Proposed Design Outline

### Goals
- Close OOS #3161: prove the Step 0b router-flag recovery merge is bypassed on a hard `write-run-params.sh` failure.
- Add an executable case to `test-step0b-router-flag-recovery.sh` that injects a failing writer and asserts the modeled flow aborts *before* recovery runs.
- Add a success-path positive control so the abort assertion cannot pass trivially.

### Non-goals
- No change to `/design` SKILL.md Step 0b behavior (writer failure stays a hard `exit 1` abort; recovery stays post-success-only).
- No new `scripts/test-design-structure.sh` pin (per Round 1 scope decision).
- No change to existing cases 1–6 or the `merge_run_params()` / `recovery_merge_if_needed()` helper contracts.

### Approach sketch
- Add a harness-local helper modeling SKILL.md Step 0b sub-step 6: run the writer; on non-zero exit, return the abort code *without* calling `recovery_merge_if_needed`; on success, call recovery.
- Use a recovery "spy" sentinel the helper touches immediately before recovery, so the test proves whether recovery was reached.
- Inject the failure with the real `write-run-params.sh` given invalid argv (e.g. `--classification BOGUS`) — no mock script needed.
- New Case 7: failing writer → non-zero return + spy absent (recovery bypassed); positive control → success → spy present + merge applied.

### Surfaces in scope
- `scripts/test-step0b-router-flag-recovery.sh` — add the modeling helper + Case 7.
- `scripts/test-step0b-router-flag-recovery.md` — document the new coverage closing #3161.

### Open questions
- None.
