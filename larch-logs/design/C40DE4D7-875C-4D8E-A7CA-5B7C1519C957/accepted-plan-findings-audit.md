Accepted plan-review findings audit — Gate C

STRONG-DISAGREE (accepted by vote, intentionally NOT applied per operator directive that overrides issue acceptance criterion 4):
- FINDING_4 (round 1: "PR #6706 still needs the Section E table in its body"). Section: Scope / docs/workflow-lifecycle.md. Rationale: contradicts discussion-round1.md Decision 1 and the approved design-outline.md non-goal — operator directed "no editing already-merged PRs; all new work in new PRs." Satisfied instead by a durable committed record of the Section E table in docs/workflow-lifecycle.md.
- FINDING_9 (round 1: [SCOPE-REDUCTION] "drop the docs update and add gh pr edit 6706"). Section: Scope / Approach. Rationale: same operator directive; the committed-docs record is retained deliberately, and the PR-#6706 body mutation is rejected.

AGREE (accepted and applied to plan.txt):
- FINDING_3 / FINDING_1 (recycled-PID reap must hit the expired terminate branch, not both-dead fast-unlink). Section: scripts/test-bgjob.sh scenario 5 + Edge cases. Applied: scenario 5 keeps daemon liveness live, forces expiry, corrupts only child identity on a live recycled PID.
- FINDING_5 round 1 (reap_main terminate-branch preconditions). Section: test_reap.py case 2. Applied: daemon_live=True, child_live=False, expired.
- FINDING_5 round 2 (budget-expiry must prove the child group was killed). Section: scripts/test-bgjob.sh scenario 3. Applied: capture child identity pre-wait, assert not live post-timeout.
- FINDING_6 (timing helper env reads must resolve at call time, not import time). Section: daemon.py. Applied: call-time resolution note; existing monkeypatch tests preserved.
- FINDING_7 (env-via-config baseline needs a reason path for new reads). Section: env-via-config-constant-baseline.json + daemon.py. Applied: route reads through config.ENV_TEST_* constant (no new baseline rows) or add per-read pragmas.

Application fidelity: every final-plan change traces to an accepted finding, the operator directive, or postplan validation. No unexplained plan changes. plan-before-review.txt vs plan.txt end-state diff reflects the applied reap/budget/timing/baseline findings plus the operator-directed committed-docs approach.

Overall: STRONG dissent present, limited to the two PR-#6706-body findings, driven entirely by the explicit operator directive (not a technical disagreement with the reviewers' AC reading).
