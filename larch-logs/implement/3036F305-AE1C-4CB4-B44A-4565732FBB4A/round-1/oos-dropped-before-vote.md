### OOS_1: [OUT_OF_SCOPE] stale ship refresh can re-merge difficulty data after failed restage
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-runlog-restage
- **Severity**: latent
- **Concern**: Ship-time refresh still rebuilds from the staged `difficulty-rating.json`, so a fail-open restage miss or a resumed/detached flush without tmpdir state can reintroduce stale audit/escalation nulls into the committed batch instead of preferring the fresher tmpdir record when it exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Prefer implement tmpdir difficulty-rating.json during ship refresh when the file exists and is readable.
  - From dyn-dyn-runlog-restage: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] flush-failure path lacks a restage regression test
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: There is no test pinning the Step 5 flush-failure path, so a regression could move restaging under the failing flush try block and silently skip the difficulty-rating write when `flush_review_batches` raises.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add or extend a test that flush failure still triggers run-log write --batch difficulty-rating.
  - From cursor-specialist-testing: Extend the test with a tmpdir difficulty-rating.json mock _run and assert run-log write --batch difficulty-rating still runs with --input-file pointing at the tmpdir record after flush_review_batches raises.

### OOS_3: [OUT_OF_SCOPE] restage tests only validate argv, not staged file contents
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The current restage tests check command-line arguments only, so a bug in copying or resolving the staged JSON on disk would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Optionally have fake_run copy --input-file into the staged log path and assert resolved audit_escalation fields.

### OOS_4: [OUT_OF_SCOPE] internal-error path still skips difficulty restage
- **Reviewer(s)**: dyn-dyn-runlog-restage
- **Severity**: latent
- **Concern**: The Step 5 internal-error exit path still never restages difficulty after tier resolution, which can leave the committed rating at the earlier staged value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-runlog-restage: Pre-existing; call _flush_review_batches_for_result or _restage_difficulty_batch_fail_open on that path if desired.

### OOS_5: [OUT_OF_SCOPE] explicit self-review bypasses Step 5 restaging
- **Reviewer(s)**: dyn-dyn-runlog-restage
- **Severity**: latent
- **Concern**: Explicit `--self-review` skips `review-and-fix step5`, so difficulty restaging never runs on that orchestrator path and the committed `difficulty-rating.json` can stay at the bootstrap value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-runlog-restage: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] missing coverage for other flush-invoking terminal paths
- **Reviewer(s)**: dyn-dyn-runlog-restage
- **Severity**: nit
- **Concern**: The new tests do not cover stall, `self-review-required`, or `mav-resume-past-cap` exits even though those terminal paths also call `_flush_review_batches_for_result`, so a second flush call could still slip through unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-runlog-restage: A parameterized stall-path test would lock in the single-flush contract above.

