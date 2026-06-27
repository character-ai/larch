### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step3b-tail.md:24
- **Concern**: Plan delegates Step 4 tail dialectic detail to `design-step3b-tail.md` but lists no `### UPDATED:` entry for that file.. Scenario: Invariant line 24 still says the orchestrator backgrounds the whole tail fence when debate may run, re-anchoring deleted `_step4_debate_may_run` self-compute after SKILL.md moves eligibility to Step 3b finalize `STEP4_MODE`. Wrapper-doc readers can implement the old predicate.
- **Proposed resolution**: Add `### UPDATED: skills/design/scripts/design-step3b-tail.md`: replace line 24 with STEP4_MODE=background orchestrator backgrounding (probe decided in finalize); add a matching `not_contains`/`contains` pin in `scripts/test-design-structure.sh` if agent-lint relies on wrapper invariants.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:155-157
- **Concern**: Step 3 entry dedup test pins are positive-only (`one parameterized Step 3 entry fence`, preserved `--reentry` note) with no structural negative guard for the duplicate bash fences at `skills/design/SKILL.md:524-532`.. Scenario: An implementer can add parameterized prose while leaving both `design-step3-entry.sh` and `design-step3-entry.sh --reentry` fences; `make test-design-structure` still passes and issue mechanism #3 (~conditional lines) ships incomplete.
- **Proposed resolution**: Add `contains` for ``design-step3-entry.sh ${STEP3_REENTRY_FLAG}`` (or equivalent) plus `not_contains` for a second standalone ``design-step3-entry.sh --reentry`` bash fence (or an assert that only one Step 3 entry launcher fence remains).



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3b-tail.md:24
- **Concern**: Step 4 tail wrapper doc is not listed for update though SKILL delegates tail routing detail there. Line 24 still says the orchestrator backgrounds the whole tail fence when debate may run, re-anchoring deleted `_step4_debate_may_run` / prompt-side probe semantics after finalize owns eligibility via `STEP4_MODE`.. Scenario: An implementer can rewrite `SKILL.md` Step 4 to bind `STEP4_MODE` only, skip `design-step3b-tail.md`, and leave the cited wrapper doc instructing orchestrators to decide backgrounding from debate-may-run heuristics. Agent-lint and pause/resume readers then get contradictory authority on the Step 4 launch contract.
- **Proposed resolution**: Add `### UPDATED: skills/design/scripts/design-step3b-tail.md`: replace the orchestrator-background-when-debate-may-run invariant with `STEP4_MODE=foreground|background` from Step 3b finalize (or `.step4-mode.env` on resume); state orchestrator selects `run_in_background` from that durable mode only; add a matching `not_contains` pin in `scripts/test-design-structure.sh`.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:479-480
- **Concern**: Plan rewrites settle fallback prose and updates several settle-dispatch pins, but it never names the two `assert_followed_count_at_least` harness rows that still require deleted Gate A/B fallback step-2 strings in `SKILL.md`.. Scenario: The plan adds `not_contains` guards and rewrites `approval-gates.md` / `discussion-rounds.md` assert strings, yet pins at lines 479-480 still require `Use the **Gate A / discussion-round2** fallback row` and `Use the **Gate B** fallback row`. Implementers can follow the listed test edits, update prose, and still hit a confusing `make test-design-structure` failure until they discover these orphaned pins ad hoc.
- **Proposed resolution**: Extend the `scripts/test-design-structure.sh` section to explicitly rewrite both `assert_followed_count_at_least` rows at 479-480 to the collapsed table-only step-2 contract (require `SETTLE_NEXT_ACTION`, stop if absent, no fallback-row phrase, no rc `10`/`12`/`13` map tails), alongside the existing 477-478 updates.



### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3b-entry.sh:88-100
- **Concern**: run_step3b_finalize still writes .completed/step-3b before the new probe-only STEP4_MODE handoff. Scenario: The plan asks finalize mode to probe dialectic eligibility and emit STEP4_MODE, but the marker is already touched inside run_step3b_finalize. A probe failure or pause between finalize and Step 4 will look like Step 3b completed even though the new Step 4 contract never finished, which can misroute resume logic.
- **Proposed resolution**: Move the .completed/step-3b touch out of run_step3b_finalize or after the probe and STEP4_MODE emission succeed, and update the matching SKILL.md / design-step3b-entry.md wording to match



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step3b-tail.md:24
- **Concern**: Plan cites design-step3b-tail.md as Step 4 tail routing detail but omits a ### UPDATED entry; line 24 still says the orchestrator backgrounds the tail when debate may run.. Scenario: After SKILL drops _step4_debate_may_run and binds STEP4_MODE from finalize, the cited wrapper doc still anchors deleted orchestrator self-compute semantics. An implementer can update SKILL and the shell while leaving tail.md unchanged; no test pin covers this file.
- **Proposed resolution**: Add ### UPDATED: skills/design/scripts/design-step3b-tail.md: replace line 24 with STEP4_MODE foreground/background routing (debate eligibility decided in finalize probe-only); state orchestrator backgrounds only when STEP4_MODE=background. Add a matching contains/not_contains pin in scripts/test-design-structure.sh.



### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:98-105
- **Concern**: Calls out `design-step3b-tail.md` as the place to move Step 4 tail behavior, but never lists that file for update.. Scenario: `skills/design/scripts/design-step3b-tail.md:21-24` still says the orchestrator backgrounds the tail and runs `dialectic-gatec` before preview, so the new `STEP4_MODE` authority in `SKILL.md` conflicts with a loadable doc the plan leaves untouched.
- **Proposed resolution**: Add `### UPDATED: skills/design/scripts/design-step3b-tail.md` and rewrite the stale invariant so Step 4, not the wrapper, owns foreground/background routing from `STEP4_MODE`.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3b-tail.md:24
- **Concern**: Plan delegates Step 4 tail dialectic detail to design-step3b-tail.md but omits that file from Files to modify/create. Line 24 still assigns backgrounding to the orchestrator when debate may run, reviving deleted _step4_debate_may_run semantics after SKILL.md binds STEP4_MODE only.. Scenario: An implementer can update SKILL.md and design-step3b-entry.sh per the plan yet leave the cited wrapper doc saying the orchestrator backgrounds the whole tail fence when debate may run. Pause/resume and agent-lint readers then follow stale debate-may-run routing instead of STEP4_MODE=foreground|background from finalize.
- **Proposed resolution**: Add ### UPDATED: skills/design/scripts/design-step3b-tail.md: replace line 24 with STEP4_MODE contract (orchestrator selects foreground vs background from finalize stdout or .step4-mode.env; tail runs dialectic-gatec internally when needed). Add a matching not_contains pin in scripts/test-design-structure.sh if other wrapper docs are guarded.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/shared/design-background-wait.md:50-52
- **Concern**: Step 4 background path still mandates READ of design-background-wait.md, but the plan does not update its Step 4 post-notification section. It frames backgrounding as the debate path rather than STEP4_MODE=background decided in Step 3b finalize.. Scenario: After SKILL.md removes orchestrator debate self-compute, the shared wait doc still tells readers to background the tail for the debate path. Resume and background-wait callers can mis-parse eligibility as Step 4-owned instead of durable STEP4_MODE from finalize or .step4-mode.env.
- **Proposed resolution**: Rewrite ## Step 4 post-notification sequence to key off STEP4_MODE=background (debate required at finalize probe) instead of debate path / debate may run wording. List skills/shared/design-background-wait.md under Files to modify/create.



### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:233-242
- **Concern**: Testing strategy only adds structure pins and `python/test_design_dialectic.py`; it never calls out an executable check for the new `STEP4_MODE` handoff or the `resume@4` sidecar fallback.. Scenario: A broken finalize stdout contract, malformed `.step4-mode.env`, or a `resume@4` path that ignores the sidecar can still ship green because the planned checks only grep prose. Add a focused runtime test that drives `design-step3b-entry.sh --mode finalize`, asserts the single `STEP4_MODE=` line and sidecar write, then re-enters Step 4 with only the sidecar present and verifies malformed or missing probe output fails closed.
- **Proposed resolution**: 



