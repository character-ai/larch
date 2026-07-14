### FINDING_2: Gate C plan-revise re-entry lacks an explicit settle/postplan contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Plan revisions do not identify a Gate C settle site, required result handling, or the exact return point for fresh reassessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `--site gate-c` (or equivalent) to `design-step35-settle.sh`, `settle_next_action_for`, `settle-rc-dispatch.md`, and `approval-gates-gate-c.md`, with rc-0 routing back to `resume@4b` rather than Gate A
  - From Cursor-Pragmatic: Add an explicit Gate C post-revision contract: name the wrapper/CLI (`design postplan-emit` or `design step2b-postplan` with a new `gate-c` site), required KVs/rc handling, and the exact re-entry point back to Gate C presentation.


### FINDING_3: Gate C structure pins are omitted from the firm change set
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Dyn Gatec Ladder
- **Severity**: major
- **Concern**: Replacing the inline remediation loop will invalidate existing structure-pin needles unless the pins are updated to assert the new ladder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/tests/skills/skill_structure_pins.py` (and any specialized Gate C ordering checks) with new needles for the two-tier ladder, per-kind counters, plan-revise spawn, and cancellation terminal flow (G-Fix-1)
  - From Cursor-Innovation: Add ### UPDATED: python/tests/skills/skill_structure_pins.py (and any dependent harness rows) with pins for the two-tier per-kind ladder, tier counter paths, and cancellation terminal flow
  - From Codex-Innovation: Add this file to the plan and replace the obsolete pins with tiered-ladder, fresh-rejudge, bound, and exception-disclosure assertions.
  - From Cursor-Pragmatic: Add `### UPDATED: python/tests/skills/skill_structure_pins.py` with new per-kind tier-counter and ladder needles; drop or replace the retired remediation pins in the same change.
  - From Cursor-Requirements: make test-design-structure fails until python/tests/skills/skill_structure_pins.py pins are revised for per-kind tier counters MODE=plan-revise and the new cancellation path.
  - From Codex-Requirements: Add `python/tests/skills/skill_structure_pins.py` to the plan and replace the obsolete loop/counter pins with ladder-specific assertions
  - From Cursor-dyn-Dyn Gatec Ladder: Add ### UPDATED: python/tests/skills/skill_structure_pins.py with new needles for tier-1/tier-2 ladder, per-kind counter paths, plan-revise spawn, and fresh-assessor-after-fix contracts; drop obsolete inline-rewrite pins.


### FINDING_4: Final-summary renderer does not disclose persisted guideline exceptions
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Dyn Gatec Ladder
- **Severity**: major
- **Concern**: The required validated `Exception:` disclosure under `--skip-approve` is not assigned to the final-summary renderer and tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/larch/design/design_summary.py` (and tests in `python/tests/design/test_design_summary.py`) to read the persisted guideline assessment, surface a validated active `Exception:` line in terminal summaries on the auto-approve path, and pin the behavior in Gate C prompt-contract tests
  - From Cursor-Innovation: Add ### UPDATED: python/larch/design/design_summary.py (and tests) to surface a persisted guideline exception block in the terminal summary on approved and --skip-approve paths
  - From Codex-Innovation: Add `design_summary.py` and `python/tests/design/test_design_summary.py` to render the validated persisted exception in the final summary.
  - From Cursor-Pragmatic: Extend `design_summary.py` (and any render caller) to surface a validated guideline exception from `architectural-guideline-assessment.md` under `--skip-approve`; add/extend tests beyond `test_architectural_guidelines.py`.
  - From Codex-Pragmatic: Add `python/larch/design/design_summary.py` and `python/tests/design/test_design_summary.py` to render the validated persisted exception in the final summary, including the `--skip-approve` path.
  - From Cursor-Requirements: ### UPDATED python/larch/design/design_summary.py (and tests): when skip_approve and persisted guideline assessment carries a validated Exception line include it in the terminal final-summary body.
  - From Codex-Requirements: Add renderer support to read and safely render the persisted valid exception in `final-summary.md`, with focused summary tests
  - From Cursor-dyn-Dyn Gatec Ladder: Add ### UPDATED: python/larch/design/design_summary.py (and finalize-step5.md Step 5c refusal table) to surface persisted Exception lines in terminal summary and to handle the new bare-deviation publish refusal with Return to Gate C.


### FINDING_5: Invalid-deviation publish refusal lacks Step 5c repair routing
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Dyn Gatec Ladder
- **Severity**: major
- **Concern**: A new publish refusal for a bare or malformed guideline deviation is not mapped to a documented Return-to-Gate-C or cancellation branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add Step 5c and skills/design/references/finalize-step5.md handling for the new refusal (Return to Gate C / Cancel) mirroring missing-guideline-assessment, and cover it in python/tests/design/test_design_publish.py / test_design_lifecycle.py
  - From Cursor-Pragmatic: Add the new refusal token to `SKILL.md` validator-failure / Step 5c branches and `finalize-step5.md`, mirroring the existing missing-assessment Return-to-Gate-C / Cancel contract.
  - From Cursor-Requirements: Add ### UPDATED entries for skills/design/references/finalize-step5.md python/larch/design/design_step5c.py and the Step 5c validator section in skills/design/SKILL.md with Return to Gate C routing for the new PUBLISH_REFUSE_REASON.
  - From Cursor-dyn-Dyn Gatec Ladder: Add ### UPDATED: python/larch/design/design_summary.py (and finalize-step5.md Step 5c refusal table) to surface persisted Exception lines in terminal summary and to handle the new bare-deviation publish refusal with Return to Gate C.


### FINDING_11: Publish gate does not explicitly reject invariant violation assessments
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-Dyn Gatec Ladder
- **Severity**: major
- **Concern**: Presence-only invariant assessment checks could allow stale or violating assessment notes to publish, contrary to the never-publishable invariant rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend design_publish completeness to read the invariant assessment and refuse publish with a stable PUBLISH_REFUSE_REASON when state is violation; add matching tests in python/tests/design/test_design_publish.py.
  - From Cursor-dyn-Dyn Gatec Ladder: Extend design_publish.py (and degraded log-publish sibling) to read the safe assessment boundary and refuse invariant non-clean notes with a stable PUBLISH_REFUSE_REASON routing back to Gate C; mirror in finalize-step5.md and SKILL.md Step 5c.


### FINDING_7: Exception disclosure lacks secret redaction
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: A validated exception rationale is appended to an issue-upserted final summary without a redaction requirement, so secret-shaped values from the plan or note could be published.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add secret redaction before appending the exception disclosure and test that a valid exception with a secret-shaped rationale is redacted in the final summary.


### FINDING_8: Tier-2 counters lack defined consumption points
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Concern**: The plan does not define when tier-2 counters are consumed. Repairs, failed settles, pause/resume, or guideline declines could re-enter Gate C without charging the round, violating the one-round-per-kind bound.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Specify atomic tier-2 counter consumption before each main-agent repair or guideline decline, including failed-settle recovery, and add pause/re-entry coverage for that bound.


### FINDING_9: Generated implementer outputs are omitted
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Changes to `agents/_implementer-base.md` would leave the generated external implementer prompts stale, causing agent-sync or generation checks to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add `agents/codex-implementer.md` and `agents/cursor-implementer.md` as regenerated updated files; run both generators and `python3 python/cli.py generate check`.


