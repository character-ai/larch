### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-step-5-review.sh:239-266
- **Concern**: Plan failure mode #2 and the live-registry wrapper change lack a harness case. Scenario: The plan clears non-complete canonical result envs before live `bgjob wait`, but also says to keep live-registry tests unchanged. Today only the no-registry stall path is rewritten; a regression that still replays cached stall during live rejoin would not fail CI
- **Proposed resolution**: Add a live-registry case that seeds a canonical stall result env, runs the wrapper with `STEP5_REGISTRY_MODE=live`, and asserts the result env is removed and `bgjob wait` is invoked without a fresh `bgjob start`; drop the keep-unchanged instruction for live-registry tests

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/review/review_core_body.py:155-197
- **Concern**: All-NOT_SUBSTANTIVE coverage must consult dropped-slot genuine failures, not only collector rows. Scenario: Approach requires no mixed real failure per archetype, but the UPDATED bullets only describe collector slug tracking. A slug with one NOT_SUBSTANTIVE collector row and a dropped genuine failure for the other vendor could still be added to the all-NOT_SUBSTANTIVE success set and pass coverage incorrectly
- **Proposed resolution**: Before adding a slug to all-NOT_SUBSTANTIVE coverage, exclude any slug present in dropped-file genuine-failure sets (same rule as `_straggler_excused_static_slugs`); extend the negative unit test with NOT_SUBSTANTIVE in collector plus dropped genuine failure for the same archetype

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:16-17
- **Concern**: Does not list `skills/implement/SKILL.md`, so the authoritative Step 5 contract at `skills/implement/SKILL.md:482-488` will still say cached stall result envs are terminal-reused.. Scenario: Operators and future edits will keep following the stale stall-reuse rule, which conflicts with the planned fresh-start recovery path.
- **Proposed resolution**: Add `### UPDATED: skills/implement/SKILL.md` and rewrite the Step 5 prose to distinguish live-registry rejoin from cached-stall fresh start.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: plan.txt:41-49
- **Concern**: The test plan never exercises the new live-registry path that clears a non-complete canonical result env before `bgjob wait`.. Scenario: A regression in that clear-before-wait branch would still pass the current live-registry test because it only covers an empty result env.
- **Proposed resolution**: Add a dedicated `skills/implement/scripts/test-step-5-review.sh` case that seeds a valid stall result env with a live registry row and asserts the canonical result env is removed before rejoin.

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-review.sh:205-209
- **Concern**: 1. Clearing any non-complete canonical result env in the live-registry branch will delete a valid stall envelope before bgjob wait can consume it.. Scenario: A run that has already written `STEP5_REVIEW_STATUS=stall` can still show a live registry row for a short window. Deleting the env makes re-entry miss the terminal stall and can block or misroute recovery.
- **Proposed resolution**: Preserve valid stall envelopes when `registry_state=live`. Only delete malformed or partial result envs that lack the stall or completion KVs.

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-step-5-review.sh:260-285
- **Concern**: 2. The wrapper test suite does not cover the new live-registry plus valid stall-env path introduced by the branch change.. Scenario: The plan adds live-registry clearing behavior for non-complete result envs, but the current tests only cover live rejoin with no result env and dead/timeout/orphaned waits. A regression that drops a terminal stall envelope would still pass.
- **Proposed resolution**: Add one live-registry case that seeds a valid stall canonical result env and verifies the wrapper still reaches bgjob wait without deleting that env.

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-step-5-review.sh:241-265
- **Concern**: Live-registry clearing for cached stall is not verified. Scenario: The new no-live canonical-stall test never exercises the failure mode called out in the plan, where a live identity-valid registry row can still read stale terminal state unless the cached stall env is cleared before wait
- **Proposed resolution**: Add one live-registry case that seeds a valid stall result env, asserts it is removed or ignored before `bgjob wait`, and confirms the wrapper reuses the live bgjob without starting a second daemon

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-Step5 Recovery Contract
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-5-review.sh:130-145,239-246
- **Concern**: Rewriting the only stall-result case away from the `done-stall` branch exercised by `seed_stall_result_env()` removes coverage for the valid final `bgjob wait` stall path.. Scenario: No harness case would still assert that a terminal stall envelope is consumed through `bgjob wait` and reaches the Step 18 routing path.
- **Proposed resolution**: Keep one test that drives `STEP5_WAIT_MODE=done-stall` and asserts the stall envelope is consumed; add a separate fresh-start cached-stall test instead of replacing it.

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-Step5 Recovery Contract
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-5-review.sh:88-132,205-214; skills/implement/scripts/test-step-5-review.sh:260-266
- **Concern**: The unchanged `live registry` harness case calls `step5_live_registry_exists()` but never seeds a canonical stall result env, so it cannot exercise the new clear-before-wait branch in `step5_canonical_result_env_state()`.. Scenario: A stale `implement-step5-review.result.env` could survive beside a live registry row and the wrapper would rejoin without proving that non-complete canonical state is cleared first.
- **Proposed resolution**: Add a live-registry fixture that seeds a stall canonical result env, asserts it is removed, and still sees the wrapper rejoin via `bgjob wait` without spawning a second daemon.
