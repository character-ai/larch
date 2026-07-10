### FINDING_1: Missing Step 5c invariant-refusal dispatch
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The Step 5c orchestrator surface still has no invariant-refusal branch, so `missing-invariant-assessment` can fall through to validator autofix/Override or the wrong prompt path instead of the Return-to-Gate-C / Cancel flow, especially when it should be evaluated before the guideline/review-provenance branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/design/SKILL.md; insert **Step 5c missing-invariant-assessment** before the existing missing-guideline case (evaluate invariant refusal first when both could apply); mirror finalize-step5 skip-autofix/Override and Return to Gate C / Cancel contract
  - From Codex-Arch: Add the invariant refusal clause beside `missing-guideline-assessment` in the shared Step 5c special-case block and pin it in the structure harness.
  - From Cursor-Innovation: Add ### UPDATED: skills/design/SKILL.md with a Step 5c missing-invariant-assessment special case before missing-guideline-assessment and before review-provenance, mirroring the guideline bullet, and pin it in scripts/test-design-structure.sh.
  - From Cursor-Pragmatic: Add ### UPDATED: skills/design/SKILL.md: insert **Step 5c missing-invariant-assessment** before the guideline case, keyed on PUBLISH_REFUSE_REASON=missing-invariant-assessment, with Return to Gate C naming architectural-invariants present-note/persist; pin the prose in scripts/test-design-structure.sh
  - From Cursor-Requirements: Add `### UPDATED: skills/design/SKILL.md` with a **Step 5c missing-invariant-assessment** block keyed on `PUBLISH_REFUSE_REASON=missing-invariant-assessment`, placed before the guideline special case; mirror skip-autofix/Override and Return/Cancel semantics


### FINDING_3: Invariant refusal recovery path is not fully pinned
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Run Log Integrity
- **Severity**: major
- **Concern**: The Step 5c refusal-chain update still lacks invariant-first evaluation order and a complete Return-to-Gate-C recovery path using invariant verbs, so operators may copy the guideline repair sequence or place the invariant case after guideline recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Insert missing-invariant-assessment before missing-guideline-assessment in the Step 5c special-case list; add Return path Step 4b (resume@4b) → architectural-invariants present-note → architectural-invariants persist-design-assessment → design-step5c.sh with the planned invariant warning text
  - From Cursor-Pragmatic: Insert missing-invariant-assessment before missing-guideline-assessment; Return: resume@4b → architectural-invariants present-note → architectural-invariants persist-design-assessment → design-step5c.sh; pin in scripts/test-design-structure.sh
  - From Cursor-Requirements: In `finalize-step5.md`, add a `missing-invariant-assessment` branch before the guideline branch with Return: Step 4b → `architectural-invariants present-note` → `architectural-invariants persist-design-assessment` → `design-step5c.sh`; keep guideline Return unchanged
  - From Cursor-dyn-Run Log Integrity: Add a full rc=4 branch before `missing-guideline-assessment`: `PUBLISH_REFUSE_REASON=missing-invariant-assessment` → Return to Gate C / Cancel with Return `Step 4b (resume@4b) → architectural-invariants present-note → architectural-invariants persist-design-assessment → design-step5c.sh`; pin it in `scripts/test-design-structure.sh`.


### FINDING_4: Approved-partition invariant artifact gating is incomplete
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: major
- **Concern**: The invariant required-artifact helper still misses approved-partition outcomes, so approved design runs can omit `architectural-invariant-assessment.md` without failing completeness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Gate the invariant helper with the same approved predicate as the guideline helper, or explicitly include `approved-partition`.
  - From Codex-Innovation: Mirror _design_run_approved here and require the invariant artifact for both approved and approved-partition outcomes, then add a partitioned test case.


### FINDING_5: Step 5c refusal status mapping needs a third branch
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The `publish_rc=4` mapping is still binary, so `missing-invariant-assessment` can be mislabeled as validator-defects instead of its own refusal class.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the plan design_step5c.py item to require an if/elif chain on PUBLISH_REFUSE_REASON (missing-invariant-assessment, missing-guideline-assessment, else validator-defects) and add a dedicated test_step5c_core_rc4_missing_invariant_assessment_not_validator_defects sibling in test_design_lifecycle.py.


### FINDING_1: Gate C persist dispatch is underspecified
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The Gate C prose lists persist branches but does not say when to choose clean vs remediated-violations vs absent/invalid. That leaves an approval run able to persist a clean invariant assessment even after violations were discovered and remediated, which would drop the required audit trail for the invariant check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: `Mirror the guideline persist dispatch shape: **Clean** only when invariants are present with parsed non-empty content and no violation assessment was required; **Remediated-violations** when violations were identified and the remediation loop produced a clean plan (write a short summary to "$DESIGN_TMPDIR/architectural-invariant-assessment.input.sidecar", then persist with --assessment-file); **Absent, invalid, or present-but-empty** when read_invariants().status is not present or parsed content.strip() is empty (no assessment flags). Pin the dispatch prose and branch order in scripts/test-design-structure.sh alongside the existing persist-command pins.`


