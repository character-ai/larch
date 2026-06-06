### FINDING_1: HARD round-1 assessor harness still expects skip
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Requirements, Cursor-Pragmatic, Codex-dyn-harness-gap
- **Severity**: important
- **Concern**: HARD round-1 plan-quality-assessor fixtures, especially case #4c/D2C, still assert the assessor is skipped even though round 1 now dispatches against `plan.txt-original`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rewrite D2C (and handoff cases D1B/D1C) to expect round-1 assess dispatch with plan.txt-original anchor; drop ASSESSOR_STATUS=skipped expectations
  - From Cursor-Edge: make lint fails on test-design-plan-quality-assessor.sh Rewrite #4c to expect round-1 assessor dispatch (or TIE/not-worse with round-1 stubs), mirroring the new round-1 contract; do not leave HARD-only skip assertions
  - From Cursor-Requirements: Rewrite case 4c (and note it in the Testing strategy) so round 1 expects assess dispatch anchored to plan.txt-original with ASSESSOR_STATUS=ok or degraded-default-open—not skipped—and optionally add a round-1 WORSE-majority rc=10 path tier-agnostic with the existing trailer assertions
  - From Cursor-Pragmatic: Update `apply_step3_6_handoff` in the same change as SKILL.md Step 3.6; rewrite SIMPLE handoff cases and case 4c (HARD round-1 assess was skipped, now must run after `ROUND_NUM < 2` removal)
  - From Codex-dyn-harness-gap: Update apply_step3_6_handoff to invoke the driver for SIMPLE, and change or remove the round-1 skipped fixture so it expects assessor invocation/result rather than skipped.

### FINDING_2: Postplan emit WARN harness cases are orphaned
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Removing `WORKFLOW_PATH` / classification coupling from `design-postplan-emit.sh` leaves classification WARN tests asserting behavior that will no longer be emitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Explicitly drop or relocate those WARN assertions when deleting WORKFLOW_PATH resolution; keep tier-agnostic snapshot taken/preserved coverage only
  - From Cursor-Pragmatic: List each classification fixture to delete or rewrite when snapshot becomes tier-agnostic (not only D2e `skipped-not-hard`)

### FINDING_3: SKILL.md HARD-only prose cleanup is incomplete
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` still has HARD-only Step 3.6 prose in Gate B handoff/helper catalog text after the plan opens the assessor to SIMPLE.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add both lines to the SKILL.md update step alongside the three mentions already listed

### FINDING_4: Approval-gate and plan-review docs still describe HARD-only Step 3.6 behavior
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-dyn-harness-gap
- **Severity**: important
- **Concern**: Nearby `approval-gates.md` and `plan-review.md` prose still says Step 3.6, zero-findings/all-rejected paths, or round-cursor advancement apply only on HARD runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Same edit pass: remove HARD-only link text and replace on HARD runs qualifiers with both-tier wording
  - From Cursor-Pragmatic: Add `skills/design/references/plan-review.md` (and approval-gates.md line-84/167 tier-only cursor prose) to doc updates or accept deliberate doc drift
  - From Codex-dyn-harness-gap: Update the surrounding approval-gates prose to say Step 3.6 and round-cursor advancement apply on both SIMPLE and HARD settled review paths.

### FINDING_5: Structure test still pins retired SIMPLE skip breadcrumb
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Pragmatic, Codex-Pragmatic, Codex-dyn-orphan-var-cleanup, Cursor-dyn-harness-gap, Codex-dyn-harness-gap
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` still requires the `design_classification=${_design_classification}; skipped` Step 3.6 breadcrumb that the plan removes from `SKILL.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update or remove this structure assertion in the same change; prefer pinning the qualified `design-plan-quality-assessor.sh` invocation/no tier-skip shape instead of the retired skip breadcrumb
  - From Codex-Edge: Update or remove this structure assertion with the other Step 3.6 pin changes so it matches the new both-tier assessor path.
  - From Cursor-Pragmatic: Add removing or replacing the line-1915 pin to the `test-design-structure.sh` section (alongside the existing HARD-only comment pins)
  - From Codex-Pragmatic: Update this structure pin in the plan to remove or replace the cheap-skip breadcrumb assertion with a tier-agnostic Step 3.6 driver invocation assertion
  - From Codex-dyn-orphan-var-cleanup: Update the plan's `scripts/test-design-structure.sh` step to remove or replace this breadcrumb assertion with a both-tier assessor invocation assertion
  - From Cursor-dyn-harness-gap: Delete or replace the pin at line 1915 in the same change as the Step 3.6 fence rewrite; update the four thin-fence self-test excerpts at lines 580-631 if they still embed the tier gate
  - From Codex-dyn-harness-gap: Delete or replace the cheap-skip breadcrumb assertion with a pin for unconditional design-plan-quality-assessor.sh invocation and retained rc/trailer handling.

### FINDING_6: Existing two-entry assess-plan-round integration still encodes round-1 skip
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: `test-assess-plan-round.sh` has a two-entry HARD integration block whose first entry still expects `ASSESSOR_STATUS=skipped` and whose mocks are round-2-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Explicitly rewrite the two-entry integration: Entry 1 must expect assessor dispatch (not skipped), point the mock at round-1 output paths, and keep Entry 2 round-2 behavior; or delete/replace the block if covered elsewhere

### FINDING_7: run-step3-review success cursor-advance coverage is underspecified
- **Reviewer(s)**: Cursor-Edge
- **Severity**: nit
- **Concern**: The plan says to mirror an existing HARD success assertion in `test-run-step3-review.sh`, but the harness only appears to pin HARD write-cursor failure, leaving SIMPLE success coverage ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add a new explicit SIMPLE (and optionally HARD) success case asserting cursor advance when plan-after-round-N exists, or reference test-assess-plan-round.sh advance_step3_cursor / run-step3-review launcher integration instead of a nonexistent mirror target

### FINDING_8: Pause resume STEP=3b upgrade remains HARD-only
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Legacy SIMPLE pause markers with `STEP=3b` can resume at Step 3b and permanently skip the newly enabled Step 3.6 assessor lane.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Drop the HARD classification guard (or extend to SIMPLE) in design-pause-load.sh; add a SIMPLE legacy STEP=3b case to test-design-pause-resume.sh and list both files in the plan

### FINDING_9: SECURITY.md trust-boundary docs remain HARD-only
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-harness-gap
- **Severity**: important
- **Concern**: `SECURITY.md` still says the external assessor lane is HARD-only, misleading operators after SIMPLE also dispatches untrusted assessor output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add SECURITY.md to the plan and change the HARD-only wording to tier-agnostic Step 3.6/both tiers while preserving the existing controls; no new mechanism needed
  - From Codex-dyn-harness-gap: Add a SECURITY.md update that removes HARD-only wording and states the same bounded-output and trailer-only controls now apply on SIMPLE and HARD.

### FINDING_10: Handoff shim still mirrors the SIMPLE tier skip
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-orphan-var-cleanup, Codex-dyn-harness-gap
- **Severity**: important
- **Concern**: `apply_step3_6_handoff` and SIMPLE handoff cases still simulate the old Step 3.6 tier skip, so harness parity can expect no assessor invocation even after `SKILL.md` runs the driver for SIMPLE.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rewrite D2C (and handoff cases D1B/D1C) to expect round-1 assess dispatch with plan.txt-original anchor; drop ASSESSOR_STATUS=skipped expectations
  - From Cursor-Pragmatic: Update `apply_step3_6_handoff` in the same change as SKILL.md Step 3.6; rewrite SIMPLE handoff cases and case 4c (HARD round-1 assess was skipped, now must run after `ROUND_NUM < 2` removal)
  - From Cursor-dyn-orphan-var-cleanup: make apply_step3_6_handoff call design-plan-quality-assessor.sh unconditionally (matching the de-indented SKILL.md fence) and rewrite handoff SIMPLE cases to expect banner plus assessor lane output
  - From Codex-dyn-harness-gap: Update apply_step3_6_handoff to invoke the driver for SIMPLE, and change or remove the round-1 skipped fixture so it expects assessor invocation/result rather than skipped.

### FINDING_11: Round-1 prompt duplicates original and previous anchors without guidance
- **Reviewer(s)**: Cursor-dyn-round1-prompt-coherence, Codex-dyn-round1-prompt-coherence
- **Severity**: important
- **Concern**: On round 1, `PLAN_PREV` resolves to the same path/content as `PLAN_ORIGINAL`, but the prompt still renders both Original and Previous sections without explaining the duplicate anchor, weakening current-vs-original regression detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-round1-prompt-coherence: Add one explicit round-1 sentence when `PLAN_PREV` resolves to the same path as `PLAN_ORIGINAL` (or pass `--round-num 1`) stating verdict is Current vs Original only and Previous duplicates the anchor; spell out the exact replacement instruction text in the plan
  - From Codex-dyn-round1-prompt-coherence: Add a minimal conditional note in render-assessor-prompt.sh when original and previous inputs are the same path/content, stating that round 1 has no prior-round plan and the Previous section intentionally repeats the original anchor; add test-render-assessor-prompt.sh coverage for that identical-input prompt shape alongside the original-anchor assertion

### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/assess-plan-round.sh:21-28,127
- **Concern**: [SCOPE-REDUCTION] Plan deletes the existing --design-classification helper option instead of preserving it as a compatibility no-op. Scenario: Any direct or downstream caller that still passes the documented option will start failing with unknown option, and the extra caller/docs/test churn is not required to run the SIMPLE assessor
- **Proposed resolution**: Keep --design-classification HARD|SIMPLE accepted and validated but ignored; remove only the tier skip and stop relying on the value for behavior
