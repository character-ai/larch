### FINDING_1: [OUT_OF_SCOPE] step5 result-env classifier mislabels stall as complete
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-plan-fidelity-auto, dyn-dyn-step5-recovery
- **Severity**: major
- **Concern**: `step5_canonical_result_env_state` can treat a `BGJOB_RC=0` envelope as complete even when the recorded Step 5 status is stalled, so cached stall envelopes may be reused instead of being cleared for a fresh relaunch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-plan-fidelity-auto: Address the concern above.
  - From dyn-dyn-step5-recovery: `step5_canonical_result_env_state` labels a result env `complete` whenever `BGJOB_RC=0` and all required Step 5 keys are present, without requiring `STEP5_REVIEW_STATUS=complete` or rejecting `STEP5_REVIEW_STATUS=stall`. A canonical env with `BGJOB_RC=0` plus a stall envelope would take the reuse branch at `step-5-review.sh:212-214` instead of the stall-clearing path, reproducing the cached-stall replay this change is meant to eliminate. Today’s panel-failed child usually exits non-zero, so this is latent rather than observed, but the classifier is fail-open on an integrity-sensitive boundary. **Suggested fix:** Tighten the `complete` predicate to require `STEP5_REVIEW_STATUS=complete` (or explicitly `!= stall`), and add a harness case that seeds `BGJOB_RC=0` with `STEP5_REVIEW_STATUS=stall` and asserts a fresh start, not `bgjob wait` reuse.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=true

### FINDING_2: NOT_SUBSTANTIVE coverage ignores dropped or missing genuine failures
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, cursor-specialist-plan-fidelity-auto, dyn-dyn-step5-recovery
- **Severity**: major
- **Concern**: `not_substantive_covered` can mark a slug as covered when only one vendor returns `NOT_SUBSTANTIVE`, even if a sibling vendor is dropped, never appears in telemetry, or emits a genuine failure. That can let an incomplete or degraded panel pass the coverage gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From cursor-specialist-plan-fidelity-auto: Address the concern above.
  - From dyn-dyn-step5-recovery: `not_substantive_covered` is derived only from collector rows that actually returned, not from manifest slot completeness or `dropped_slots_file` absence. If a pair-shaped archetype lists two vendors in the manifest but only one collector record returns `NOT_SUBSTANTIVE` and the other vendor never appears in collector output or dropped-slot telemetry, the slug is treated as coverage-satisfied. The new negative test covers mixed `NOT_SUBSTANTIVE` plus real failure for the same slug, but not “silent missing vendor + sole `NOT_SUBSTANTIVE`.” That can let a degraded or incomplete panel pass the coverage gate without an explicit coverage signal that a expected reviewer never ran. **Suggested fix:** When building `not_substantive_covered`, require every manifest-listed static output for that slug to have a collector or dropped-slot record, or treat “expected reviewer missing from both collector and dropped telemetry” as uncovered; add a unit test for one `NOT_SUBSTANTIVE` return plus an unaccounted manifest slot.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_3: [OUT_OF_SCOPE] transient stall classification still burns retries
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-step5-recovery
- **Severity**: minor
- **Concern**: The transient-infra classifier was left unchanged, so unrelated panel-failed stalls can still consume Step 5 retries before the durable bail path is reached.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-step5-recovery: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_4: [OUT_OF_SCOPE] Step 5 regression coverage is still incomplete
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-step5-recovery
- **Severity**: minor
- **Concern**: The test suite still misses a full regression for the original incident shape: all-`NOT_SUBSTANTIVE` coverage, the live-registry cached-stall path, and the sentinel-removal assertion on recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-step5-recovery: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Step 5 docs still do not spell out cached-stall clearing
- **Reviewer(s)**: dyn-dyn-step5-recovery
- **Severity**: minor
- **Concern**: The Step 5 contract prose is still stale: the scripted-review docs do not explicitly say that cached complete envs are reused while cached stall envs must be cleared and relaunched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-step5-recovery: `skills/implement/SKILL.md:482-488` — The Step 5 orchestrator prose still describes only “live registry rejoin” and “stale or dead rows cleared before a fresh start,” but it never states that cached `STEP5_REVIEW_STATUS=complete` envelopes are reused while cached stall envelopes must be cleared and relaunched. `skills/implement/scripts/step-5-review.md:30` requires syncing `SKILL.md` on contract changes, and the plan’s own failure-mode note warns that stale prose can reintroduce the stall-replay defect. An operator or maintainer reading `SKILL.md` alone can still believe any valid canonical result env (including stall) is terminal-reused. **Suggested fix:** Update the Step 5 scripted-review section in `SKILL.md` to match `step-5-review.md` and `step5-review-branches.md`: cached complete-only reuse, cached stall clearing for `step5-review` recovery, and live-registry rejoin with non-complete env removal before `bgjob wait`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_6: [OUT_OF_SCOPE] cached-stall recovery leaves stale round-1 artifacts behind
- **Reviewer(s)**: dyn-dyn-step5-recovery
- **Severity**: minor
- **Concern**: Fresh starts after cached-stall recovery remove the canonical result env and terminal sentinel, but they leave prior `round-1/` review artifacts behind, which can muddy postmortems.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-step5-recovery: Address the concern above.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

