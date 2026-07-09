### FINDING_1: Step 5c needs a Gate C branch for missing-guideline-assessment
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Publish Integrity
- **Severity**: major
- **Concern**: `publish_core` rc 4 with `PUBLISH_REFUSE_REASON=missing-guideline-assessment` still falls into the review-provenance / validator-autofix paths, so operators get sent back to Step 3 or composed-plan Override instead of Gate C re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/design/references/finalize-step5.md and ### UPDATED: skills/design/SKILL.md with a Step 5c special case before review-provenance and validator-autofix, keyed on PUBLISH_REFUSE_REASON=missing-guideline-assessment, offering Gate C re-entry and Cancel only; pin the operator-visible re-entry message there.
  - From Cursor-Innovation: Add a firm ### UPDATED: skills/design/references/finalize-step5.md (and matching SKILL.md Step 5c special case before review-provenance) that branches on PUBLISH_REFUSE_REASON=missing-guideline-assessment to Gate C re-entry (resume@4b / Re-run Gate C Presentation), not validator-autofix or composed-plan Override.
  - From Cursor-Pragmatic: Add firm ### UPDATED entries for skills/design/references/finalize-step5.md and skills/design/SKILL.md. Add a Step 5c special case before review-provenance (mirror plan-size ordering): when PUBLISH_REFUSE_REASON=missing-guideline-assessment, skip validator-autofix and Override, and offer only Gate C return (Step 4b presentation plus persist-design-assessment) and Cancel. Add a dedicated publish_core refusal emitter with a Gate C directed operator message; do not reuse _emit_publish_refusal review-provenance text.
  - From Codex-Pragmatic: Add a Step 5c special case before review-provenance for PUBLISH_REFUSE_REASON=missing-guideline-assessment that preserves DESIGN_TMPDIR, skips autofix and Override, and directs Fix-and-retry to Gate C assessment persistence; mirror it in finalize-step5.md.
  - From Cursor-Requirements: Add a Step 5c special case in skills/design/SKILL.md and skills/design/references/finalize-step5.md (before review-provenance) for missing-guideline-assessment: operator message names architectural-guideline-assessment.md; Fix-and-retry resumes at Gate C (resume@4b); Cancel preserves tmpdir; no Override and no Step 3 rerun
  - From Codex-Requirements: Add a Step 5c special case for PUBLISH_REFUSE_REASON=missing-guideline-assessment before review-provenance, skip validator autofix and Override, preserve DESIGN_TMPDIR, name architectural-guideline-assessment.md, and direct Gate C re-entry/retry.
  - From Cursor-dyn-Publish Integrity: Add ### UPDATED: skills/design/references/finalize-step5.md and ### UPDATED: skills/design/SKILL.md: before review-provenance, branch on PUBLISH_REFUSE_REASON=missing-guideline-assessment; skip autofix/Override; Fix-and-retry resumes Gate C (Step 4b persist-design-assessment) then design-step5c.sh; Cancel preserves tmpdir


### FINDING_2: Missing-guideline refusal needs its own envelope
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-Publish Integrity
- **Severity**: major
- **Concern**: Reusing the generic publish refusal envelope for missing-guideline-assessment would stamp the validator-defect shape that existing Step 5c logic already interprets as review-provenance or validator failure, so the wrong recovery path can win before the new branch is reached.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a dedicated refusal emitter for missing-guideline-assessment that sets ARCH_GUIDE_* and PUBLISH_REFUSE_REASON only (leave VALIDATE_STATUS=not-run), and wire the new orchestrator special case ahead of review-provenance.
  - From Cursor-Innovation: Emit missing-guideline refusal with PUBLISH_REFUSE_REASON=missing-guideline-assessment and ARCH_GUIDE_* rows only; leave VALIDATE_STATUS unset (or not-run). Pair with the new Step 5c Gate C re-entry branch and avoid STEP5C_STATUS=validator-defects for this reason.
  - From Cursor-dyn-Publish Integrity: Add dedicated refusal emitter (not _emit_publish_refusal): print Gate C re-entry warning, emit ARCH_GUIDE_* + PUBLISH_REFUSE_REASON=missing-guideline-assessment, write .design-publish-result.env, return 4 without plan-block write; do not set VALIDATE_STATUS=defects-found unless paired with the new SKILL special case


### FINDING_5: Run-log verifier needs approved-only gating and a real repo root
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Publish Integrity
- **Severity**: major
- **Concern**: The run-log completeness rule cannot be correct unless it knows both whether the run was actually approved and which consumer repo root to inspect; otherwise placeholder roots and non-approved terminal summaries will produce false requirements or false misses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add _design_run_approved(run_dir) parsing final-summary.md outcome, append the artifact row only when approved plus read_guidelines(status=present), set slug guideline-assessment, and pin the degraded Warnings body format in tests like test_artifact_present_or_waived_matches_design_capture_warning.
  - From Cursor-Innovation: Thread repo_root through verify_run_log_completeness and required_artifacts_for_run (run_log_commit.py already has repo_root at _copy_tree_to_repo_after_completeness), or derive consumer repo root via git from the staging cwd; call read_guidelines(repo_root) before adding the artifact row.
  - From Codex-Innovation: Add an explicit approved-outcome check from final-summary.md or a dedicated manifest field, then require architectural-guideline-assessment.md only when that signal says the run is approved.
  - From Cursor-Pragmatic: Extend _required_design_artifacts with a helper that detects approved outcomes only (for example final-summary heading ## /design run ...: approved, or equivalent Outcome line). Require architectural-guideline-assessment.md only when read_guidelines(repo_root).status == present and that helper is true. Document the predicate in the plan and cover failed-plan-write vs approved cases in test_run_logs.py.
  - From Cursor-Requirements: Extend _required_design_artifacts to accept manifest; require architectural-guideline-assessment.md only when final-summary.md header outcome is approved or approved-partition; resolve consumer repo root from the run_dir tree (e.g. parent of larch-logs) before read_guidelines; keep non-approved and absent/invalid guideline cases off the required set
  - From Cursor-dyn-Publish Integrity: Gate the new RequiredArtifact on an explicit approved check (parse final-summary heading for : approved or : approved-partition per design_summary _VALID_OUTCOMES) plus read_guidelines(repo_root).status==present; keep absent/invalid guidelines and non-approved outcomes exempt


### FINDING_6: `--skip-validate` publishes still need the completeness check
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: minor
- **Concern**: The assessment gate must not be tied only to the validate-success path; if `--skip-validate` bypasses the check, approved publishes can still ship without the required assessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Place _check_guideline_assessment_completeness after the validate/skip_validate block and before redact secrets / named-block write, regardless of skip_validate.
  - From Cursor-Requirements: Call _check_guideline_assessment_completeness unconditionally after review-provenance, pause, diagram, and difficulty gates and before redaction/plan-block write regardless of --skip-validate; add a publish test with --skip-validate and missing assessment expecting rc 4 Review complete.


### FINDING_3: Step 5c rc=4 contract test blocks the new refusal class
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The current Step 5c rc=4 test hard-codes `validator-defects`, which conflicts with the new `missing-guideline-assessment` refusal path and will fail once that refusal is routed outside the validator-defect bucket.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend `### UPDATED: python/tests/design/test_design_lifecycle.py` (or equivalent): keep the validator-defect case, add a sibling test where `PUBLISH_REFUSE_REASON=missing-guideline-assessment` and `VALIDATE_STATUS=not-run` asserts a distinct `STEP5C_STATUS` (or none) and never `validator-defects`


### FINDING_4: Commit-time completeness verification loses the consumer repo root
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The main commit path calls completeness verification without the consumer repo root, so the new guideline-assessment requirement can be skipped when the run is staged from the ephemeral tmpdir source tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Pass the existing `repo_root` through `verify_run_log_completeness()` and `required_artifacts_for_run()` from `_copy_tree_to_repo_after_completeness()` so the approved design run check runs before the tree copy.
  - From Cursor-Innovation: Add `### UPDATED: python/larch/report/run_log_commit.py` passing resolved `repo_root` into `verify_run_log_completeness`; keep derive-only fallback for audit callers without cwd context.


### FINDING_6: Run-log tests can pass without guideline fixtures
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The new `guideline-assessment` rows depend on a present `ARCHITECTURAL_GUIDELINES.md` at the derived consumer root, but the planned tests can remain vacuous if they never seed that fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin fixtures: write `## /design run <id>: approved` (or `: approved-partition`) into `final-summary.md`, place a valid `ARCHITECTURAL_GUIDELINES.md` at the derived consumer root, and assert the row appears before testing missing-artifact failure


### FINDING_7: Step 5c completion sentinel is written before refusal handling
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: A missing-guideline refusal can still leave `.completed/step-5c` behind, which makes Step 6 and downstream orchestration treat the run as cleanly completed instead of fail-closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Move the `.completed/step-5c` write after refusal handling, or explicitly remove the sentinel on this refusal path before returning.


