## Decision 1: Fix location — shared helper vs. reentry block only
- **Question**: Should the fix live in `_step3_clear_downstream_sentinels()` (covers all three callers) or only in the `--reentry` block of `design-step3-entry.sh`?
- **Resolution**: Shared helper. The helper is called by `--direct-review-entry`, `--auto-continuation-entry`, and `--direct-review-pause-hygiene`. All three need the result envs cleared so the next launcher takes the fresh-start path. The helper is the DRY single fix point.
- **Source**: codebase

## Decision 2: Scope — primary fix only
- **Question**: Should the fix also add defense-in-depth plan fingerprinting in `review_provenance()`?
- **Resolution**: No. Primary fix only: clear `bgjob/design-step3-review.result.env` and `bgjob/design-step4-tail.result.env` in the shared helper, plus regression tests.
- **Source**: user

## Decision 3: Which result envs to clear
- **Question**: Only `design-step3-review.result.env`, or both Step 3 and Step 4 tail?
- **Resolution**: Both. `design-step3b-tail.sh` exhibits the same rejoin pattern for `design-step4-tail.result.env`; clearing it in the shared helper prevents stale Gate C preview.
- **Source**: codebase (issue evidence + design-step3b-tail.sh:153)
