# Review Round 2

- Mode: `diff`
- 4 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Cross-session OOS recovery skips previously filed blocks when the accepted set grows
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: Cross-session recovery in `python/larch/design/design_oos.py` skips rehydrating cached Filed URL annotations when the current accepted OOS set is a superset of the cached filed set. On a same-issue rerun, that can leave an already-filed block unannotated and eligible to be filed again instead of only filing the newly accepted blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_2: Step 5b empty-stdout retry still uses the obsolete annotate-skipped contract
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: The Step 5b retry wrapper handles the obsolete `annotate-skipped-empty-stdout` status after the generic nonzero path, but production annotate emits `annotate-failed-empty-stdout` with `NEXT_ACTION` and a nonzero rc. That means the once-only retry sentinel is bypassed on the real path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Handle annotate-failed-empty-stdout with retry-file-and-annotate before generic ann_rc failure, or align tests and docs with prompt-side retry only.
  - From codex-specialist-testing: Handle annotate-failed-empty-stdout plus retry-file-and-annotate before generic nonzero handling, and update the test to use the real status and rc.


### FINDING_3: Step 5b retry tests do not cover the production annotate-failed path
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The current empty-stdout retry test exercises the dead `annotate-skipped-empty-stdout` rc=0 branch instead of the production `annotate-failed-empty-stdout` rc=1 contract, so it does not verify that Step 5b stays incomplete and the retry handoff is preserved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Step5b empty-stdout retry test uses dead annotate-skipped-empty-stdout rc=0 path instead of production annotate-failed-empty-stdout rc=1 Bug A once-only retry and no step-5b completion are unverified on the real annotate contract; regressions can silently complete Step 5b or drop retry KVs Retest with production KVs/rc or real file_oos_annotate_main; assert no .completed/step-5b and retry handoff per finalize-step5.md


### FINDING_4: Prepare-time OOS promotion scenarios are missing regression coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The plan-listed `file_oos_prepare_main` cases are not covered, including the important-only trigger, pool-before-skip-sentinel, accepted+pool latent counting, and multi-round pool behavior. That leaves the prepare-time promotion and counting logic under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Plan-listed file_oos_prepare_main scenarios remain untested: important-only trigger, pool-before-skip-sentinel, accepted+pool latent counting, multi-round pool FINDING_4 partial fix leaves Bug B ordering and aggregate counting regressions undetected Add the four prepare tests named in the plan acceptance section
  - From cursor-specialist-testing: Design path lacks prepare-time test that important aggregate pool promotes to filing when vote-accepted sink is empty Important-only OOS can fail to file despite tally pool accumulation working Add prepare test with one important pool item and assert ready plus oos-combined.md output


