### FINDING_1: Prior-round in-flight window fallback must pin to round N−1 only
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: When `round-start-s` is absent, the planned prior-round ledger fallback for `_render_inflight_gantt` is underspecified. For round N>2, a helper that scans `max end_s` across all rounds with `round_n < N` (or otherwise resolves an ambiguous prior bound) can pick round N−2's end when round N−1 has no v1 ledger row (resume/stall gaps). That widens the in-flight window and re-leaks prior-round vendor rows under the current round heading instead of bounding to the immediate prior round or current round directory mtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Resolve prior-round end only from the v1 round row where round column equals round_num minus 1; if that row is absent use current round directory mtime never an older round end
  - From Cursor-Pragmatic: Define the helper contract: for round_num greater than 1, read max end_s only from rows where cols[1]==round, cols[3]==skill, and cols[5]==str(round_num-1); if none, fall through to current round_dir mtime — never older rounds or whole-phase window_start_s


### FINDING_2: Step 5 round-start-s regression does not assert in-flight persistence
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The proposed Step 5 regression (`test_step5_handoff_persists_round_start_without_timing` and similar) only checks `round-start-s` after the round loop returns. The reported bug is visible while `_run_round` is still blocking (live `p` during an in-flight round). A regression that persists `round-start-s` only after `_run_round` on the normal path would still pass this test yet leave the in-flight Gantt broken for the whole round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Make fake_round block on a threading.Event (or sleep) until the test asserts round-start-s exists and matches start_s, then release; or assert the file mid-round before fake_round returns


### FINDING_4: Proposed `/design` Step 3 wrapper test cannot verify live round-start-s persist
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The proposed `/design` `round-start-s` regression runs through the fake Step 3 plugin (`make_fake_step3_plugin` in `test-design-step3-review.sh`), which replaces `python/cli.py plan-review run` and never executes `review-design-step3-loop.sh`. The plan requires asserting `plan-review/round-1/round-start-s` exists after the wrapper returns, but `make_fake_step3_plugin` routes `plan-review run` to `plan-review-loop-stub.sh`, so the live loop's round-start persist path is never invoked. The test either fails after a correct implementation or gives false confidence, leaving normal-path design `round-start-s` coverage unmet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Replace the wrapper runtime assertion with a static contract check on the live loop (grep that `step3_loop_persist_round_start_s` is called inside the empty-phase branch before `run_step3_round_body`), or invoke the live loop directly with only `run_step3_round_body` stubbed. Keep `python/test_plan_review.py` embedded parity; do not rely on the fake-plugin wrapper path for runtime persist verification.


### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/render-review-phase-detail.sh:257-263; scripts/render-review-phase-detail.md:26-52; scripts/test-render-review-phase-detail.sh:436-454
- **Concern**: [SCOPE-REDUCTION] Settled per-round Gantt hardening is outside the live in-flight progress bug and changes a documented helper contract. Scenario: The in-flight leak is addressed by persisting round-start-s and hardening python/progress_report.py. Changing render-review-phase-detail.sh also flips the documented unfiltered settled-chart behavior and existing preservation fixture for an unrelated surface.
- **Proposed resolution**: Remove scripts/render-review-phase-detail.sh and scripts/test-render-review-phase-detail.sh changes from this plan. Track settled-chart skill filtering separately if still desired.


### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:55-62,105-114
- **Concern**: [SCOPE-REDUCTION] Settled-report Gantt hardening is outside the in-flight progress bug. Scenario: The feature ships with round-start persistence plus progress_report fallback/tests; changing scripts/render-review-phase-detail.sh and its harness adds cross-surface churn for already-settled charts covered by the merged sibling work
- **Proposed resolution**: Drop scripts/render-review-phase-detail.sh and scripts/test-render-review-phase-detail.sh from this PR; keep the live progress_report path and its regressions focused on in-flight charts


### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/render-review-phase-detail.sh:257-263
- **Concern**: [SCOPE-REDUCTION] Plan changes settled per-round Gantt windows and adds settled-chart harness coverage even though the issue is limited to live in-flight progress charts. Scenario: This PR would alter completed-round final/detail rendering outside the reported in-flight path, increasing regression surface and test churn without being required to make the current-round live chart correct
- **Proposed resolution**: Drop scripts/render-review-phase-detail.sh and scripts/test-render-review-phase-detail.sh from this PR; if the settled chart skill-filter leak is real, file it as an out-of-scope follow-up



### FINDING_1: Design round-start-s persist must create round directory before pre-body write
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: The planned `/design` helper `step3_loop_persist_round_start_s` is meant to run before `run_step3_round_body`, but `plan-review/round-N` is created inside the round body today. Without `mkdir -p` (or equivalent) on the parent directory first, the pre-body write can fail or no-op under `set -euo pipefail`. Then `round-start-s` never lands at round start, `_current_round_dir` can keep pointing at the prior round until the body creates the new directory, and the in-flight Gantt keeps using the phase-start fallback instead of the true round start.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In step3_loop_persist_round_start_s, mkdir -p "$DESIGN_TMPDIR/plan-review/round-${round_num}" before the write-once check, matching python/review_and_fix.py _persist_round_start (lines 1924-1928)
  - From Cursor-Pragmatic: In step3_loop_persist_round_start_s, mkdir -p "$DESIGN_TMPDIR/plan-review/round-${round_num}" before the write-once check, matching python/review_and_fix.py _persist_round_start (lines 1924-1928)
  - From Codex-Generic: Specify parent directory creation before the write, while rejecting symlink parents, then write only when round-start-s is absent and not a symlink; add a focused live-loop or sourced-helper test that proves the file exists before the stubbed body runs



