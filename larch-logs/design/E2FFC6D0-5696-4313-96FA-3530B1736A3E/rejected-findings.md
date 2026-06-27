### [Plan Review] FINDING_1

### FINDING_1: Plan omits design-step3b-tail.md update; line 24 still anchors deleted debate-may-run backgrounding
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan delegates Step 4 tail dialectic detail to `skills/design/scripts/design-step3b-tail.md` but lists no `### UPDATED:` entry for that file. Line 24 still instructs the orchestrator to background the whole tail fence when debate may run, re-anchoring deleted `_step4_debate_may_run` / prompt-side probe semantics after `SKILL.md` moves eligibility to Step 3b finalize `STEP4_MODE`. An implementer can update `SKILL.md` and shell per the plan yet leave the cited wrapper doc unchanged; pause/resume, agent-lint, and wrapper-doc readers then follow stale debate-may-run routing instead of `STEP4_MODE=foreground|background` from finalize (or `.step4-mode.env` on resume).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/design/scripts/design-step3b-tail.md`: replace line 24 with STEP4_MODE=background orchestrator backgrounding (probe decided in finalize); add a matching `not_contains`/`contains` pin in `scripts/test-design-structure.sh` if agent-lint relies on wrapper invariants.
  - From Cursor-Innovation: Add `### UPDATED: skills/design/scripts/design-step3b-tail.md`: replace the orchestrator-background-when-debate-may-run invariant with `STEP4_MODE=foreground|background` from Step 3b finalize (or `.step4-mode.env` on resume); state orchestrator selects `run_in_background` from that durable mode only; add a matching `not_contains` pin in `scripts/test-design-structure.sh`.
  - From Cursor-Pragmatic: Add ### UPDATED: skills/design/scripts/design-step3b-tail.md: replace line 24 with STEP4_MODE foreground/background routing (debate eligibility decided in finalize probe-only); state orchestrator backgrounds only when STEP4_MODE=background. Add a matching contains/not_contains pin in scripts/test-design-structure.sh.
  - From Codex-Pragmatic: Add `### UPDATED: skills/design/scripts/design-step3b-tail.md` and rewrite the stale invariant so Step 4, not the wrapper, owns foreground/background routing from `STEP4_MODE`.
  - From Cursor-Requirements: Add ### UPDATED: skills/design/scripts/design-step3b-tail.md: replace line 24 with STEP4_MODE contract (orchestrator selects foreground vs background from finalize stdout or .step4-mode.env; tail runs dialectic-gatec internally when needed). Add a matching not_contains pin in scripts/test-design-structure.sh if other wrapper docs are guarded.


### [Plan Review] FINDING_3

### FINDING_3: Orphaned assert_followed_count_at_least rows at test-design-structure.sh:479-480
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan rewrites settle fallback prose and updates several settle-dispatch pins, but never names the two `assert_followed_count_at_least` harness rows that still require deleted Gate A/B fallback step-2 strings in `SKILL.md`. Implementers can follow the listed test edits, update prose, and still hit a confusing `make test-design-structure` failure until they discover these orphaned pins ad hoc.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the `scripts/test-design-structure.sh` section to explicitly rewrite both `assert_followed_count_at_least` rows at 479-480 to the collapsed table-only step-2 contract (require `SETTLE_NEXT_ACTION`, stop if absent, no fallback-row phrase, no rc `10`/`12`/`13` map tails), alongside the existing 477-478 updates.


### [Plan Review] FINDING_5

### FINDING_5: design-background-wait.md Step 4 section still frames backgrounding as debate path
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Step 4 background path still mandates READ of `design-background-wait.md`, but the plan does not update its Step 4 post-notification section. It frames backgrounding as the debate path rather than `STEP4_MODE=background` decided in Step 3b finalize. After `SKILL.md` removes orchestrator debate self-compute, the shared wait doc still tells readers to background the tail for the debate path. Resume and background-wait callers can mis-parse eligibility as Step 4-owned instead of durable `STEP4_MODE` from finalize or `.step4-mode.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Rewrite ## Step 4 post-notification sequence to key off STEP4_MODE=background (debate required at finalize probe) instead of debate path / debate may run wording. List skills/shared/design-background-wait.md under Files to modify/create.


### [Plan Review] FINDING_6

### FINDING_6: No executable test for STEP4_MODE handoff or resume@4 sidecar fallback
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Testing strategy only adds structure pins and `python/test_design_dialectic.py`; it never calls out an executable check for the new `STEP4_MODE` handoff or the `resume@4` sidecar fallback. A broken finalize stdout contract, malformed `.step4-mode.env`, or a `resume@4` path that ignores the sidecar can still ship green because the planned checks only grep prose.
- **Suggested revisions (informational for voters; coder decides)**:
```


