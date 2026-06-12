# Review Round 2

- Mode: `diff`
- 4 accepted, 6 rejected (4 neutral)

## Accepted Findings

### FINDING_10: Step 2 dispatcher harness lacks scout sidecar coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-threading-integration-output.txt
- **Severity**: important
- **Concern**: `test-step2-dispatch.sh` does not cover external coder scout sidecar threading, eligibility marker creation, empty or invalid sidecar normalization, or fallback cleanup. The `/implement` handoff could regress without harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub-launcher tests for scout path args, marker creation on complete/needs_qa, empty manifest materialization, and cleanup on fallback/recovery.
  - From codex-specialist-testing-output.txt: Add stub complete/needs_qa external runs for Cursor and Codex that assert sidecar path forwarding, canonical empty materialization on missing/invalid sidecars, marker creation only on successful external runs, and marker/sidecar removal on fallback/recovery.
  - From dyn-threading-integration-output.txt: Add offline stub-launcher cases mirroring `scripts/test-run-step5-review.sh:139-178` but at the Step 2 dispatcher layer so threading regressions are caught where `run_launcher` is defined.


### FINDING_12: Dispatch-panel pre-scout branch coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-dispatch-panel.sh` only covers a narrow pre-scout path. Missing, empty, fully filtered, cap-zero, classifier-skip, and legacy-scout fallthrough cases are not guarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add scout_must_not_run cases for missing/empty/fully-filtered manifests, cap-zero with valid pre-scout, and skipped-* modes with --pre-scouted-manifest supplied.
  - From codex-specialist-testing-output.txt: Add the missing `--pre-scouted-manifest` cases with `SCOUT_DYNAMIC_ARCHETYPES_SH` set to the must-not-run stub, and assert `SCOUT_STATUS`, `DYNAMIC_SLOTS=0`, and no legacy scout invocation for each failure/skip path.


### FINDING_13: Drafter parser harness misses sentinel and filtering edge cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-parser-logic-output.txt
- **Severity**: important
- **Concern**: Drafter parser tests cover only a small subset of required scout sentinel, fenced example, malformed scout, filtering, capping, duplicate slug, and reserved slug cases. Parser regressions could pollute `plan.txt` or break static-only fail-open behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend codex/claude drafter harness stub modes for fatal misplaced sentinels, non-fatal post-plan malformed scout, fenced examples, and launcher filter/cap integration.
  - From codex-specialist-testing-output.txt: Add the missing Codex and Claude drafter modes/assertions in `scripts/test-launch-codex-drafter.sh` and mirror them in `scripts/test-launch-claude-drafter.sh`.
  - From dyn-parser-logic-output.txt: Add direct `parse-drafter-output.py` fixture tests (or launcher stub modes) for: inline `{"archetypes":[]}` in prose (should pass), fenced example (should pass), unclosed fence hiding in-plan manifest (should fail), and `LARCH_SCOUT_BEGIN` as an exact line inside the plan envelope (should fail).


### FINDING_9: Review-and-fix harness lacks pre-scout forwarding tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-review-and-fix.sh` does not assert that `review-and-fix.sh` forwards `--pre-scouted-manifest` and preserves `--dynamic-archetypes 0`. Core argument assembly could regress while lower-level tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add harness cases asserting --pre-scouted-manifest reaches review-core.sh in implement mode and --dynamic-archetypes 0 is preserved when run-step5-review supplies it.


