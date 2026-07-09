### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py
- **Concern**: Completeness `present` check accepts zero-byte or whitespace-only assessment files. Scenario: The helper only requires a regular non-symlink file, so an agent can `touch architectural-guideline-assessment.md`, pass publish and run-log `_verify_has_file`, and still ship an approved run with no real assessment; the original silent-miss class survives in a narrower form
- **Proposed resolution**: Treat `present` as regular file with non-empty stripped content in `_check_guideline_assessment_completeness`; mirror the rule in run-log presence (or reuse the same helper) and add tests for empty and whitespace-only files

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/run_log_manifest.py
- **Concern**: `_derive_consumer_repo_root_from_run_dir` example points at the wrong directory. Scenario: The plan says derive from the parent of `larch-logs/design/<run-id>`, which is `larch-logs/design`, not the consumer git root; `read_guidelines` there usually returns `absent`, so the new required-artifact row is skipped and post-commit completeness never fires on real runs
- **Proposed resolution**: Derive the git toplevel as `run_dir.parent.parent.parent` when the path matches `.../larch-logs/design/<run-id>`, or run `git -C run_dir rev-parse --show-toplevel`; return `None` on mismatch; pin with a fixture under a fake repo root

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/tests/design/test_design_lifecycle.py
- **Concern**: Existing Step 5c rc 4 contract test will fight the new refusal class. Scenario: `test_step5c_core_rc4_emits_validator_status_sidecars_and_no_markers` hard-requires `STEP5C_STATUS=validator-defects` for every `publish_rc=4`, but the plan routes `missing-guideline-assessment` outside that bucket with `VALIDATE_STATUS=not-run`
- **Proposed resolution**: Extend `### UPDATED: python/tests/design/test_design_lifecycle.py` (or equivalent): keep the validator-defect case, add a sibling test where `PUBLISH_REFUSE_REASON=missing-guideline-assessment` and `VALIDATE_STATUS=not-run` asserts a distinct `STEP5C_STATUS` (or none) and never `validator-defects` ## Findings ### 1. [correctness] Empty assessment files still satisfy `present` (`python/larch/design/design_publish.py`) The plan closes the silent-miss gap for a missing file, but `present` is only “regular, non-symlink file.” A zero-byte or whitespace-only file satisfies that check, passes `_verify_has_file` in run-log completeness, and still delivers no assessment. `audit_runs._guideline_assessment_scan_obj` already fails empty bodies post-commit; publish-time enforcement should match. **Suggested revision:** Require non-empty stripped content in `_check_guideline_assessment_completeness`, apply the same rule when verifying committed runs, and add tests for empty and whitespace-only files. ### 2. [correctness] Run-log repo-root derivation example is wrong (`python/larch/report/run_log_manifest.py`) For `.../larch-logs/design/<run-id>`, the consumer repo root is three levels up (same layout as `final_report._implement_tmpdir_from_run_dir`), not the parent of the run directory. Following the plan’s example yields `larch-logs/design`, where guidelines are usually `absent`, so the new `guideline-assessment` required row is never added and verification is a no-op. **Suggested revision:** Derive via `run_dir.parent.parent.parent` with a path-shape guard, or `git -C run_dir rev-parse --show-toplevel`; return `None` when derivation fails; pin in `test_run_logs.py`. ### 3. [risk-integration] Lifecycle test still pins old rc 4 status (`python/tests/design/test_design_lifecycle.py`) The plan updates `design_step5c.py` to avoid `validator-defects` for `missing-guideline-assessment`, but `test_step5c_core_rc4_emits_validator_status_sidecars_and_no_markers` still requires that status for all rc 4 exits. That test is not listed in **Files to modify/create**, so implementers can break the new routing or leave contradictory behavior. **Suggested revision:** Add `test_design_lifecycle.py` to the firm file list; split rc 4 tests so missing-guideline refusal gets its own contract assertions. --- Prior accepted items (Gate C branch, dedicated envelope, approved-only run-log gating, `--skip-validate` coverage) look addressed in the current plan. I did not re-raise rejected/neutral/OOS ledger items (shared core helper, waiver pin, marker copy side effects) without new evidence.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/run_log_commit.py:393-405
- **Concern**: Completeness check is not threaded through the actual run-log commit path.. Scenario: `_copy_tree_to_repo_after_completeness()` still calls `verify_run_log_completeness(run_dir=src, skill=skill)` on the tmpdir source tree, so `_derive_consumer_repo_root_from_run_dir()` will usually fail to recover the real consumer repo root and the new guideline-assessment requirement will be skipped on the main commit path.
- **Proposed resolution**: Pass the existing `repo_root` through `verify_run_log_completeness()` and `required_artifacts_for_run()` from `_copy_tree_to_repo_after_completeness()` so the approved design run check runs before the tree copy.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_step5c.py:624-679
- **Concern**: ARCH_GUIDE_* keys never reach the Step 5c bgjob result env.. Scenario: The plan only allowlists the new fields in `.design-publish-result.env`; `step5c_core()` still rewrites `.design-step5c-status.env` from a fixed subset, so `bgjob wait` and `design read-result-env` will drop the new refusal envelope before later steps inspect it.
- **Proposed resolution**: Add the four `ARCH_GUIDE_*` fields to the rows written to `.design-step5c-status.env` and to `STEP5C_STATUS_ALLOW_KEYS`, not just `STEP5C_PUBLISH_RESULT_ALLOW_KEYS`.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py
- **Concern**: Presence check treats zero-byte assessment files as present. Scenario: `_check_guideline_assessment_completeness` only requires a regular non-symlink file; `_verify_has_file` in `run_log_manifest.py` also uses `.is_file()` only. A zero-byte `architectural-guideline-assessment.md` passes publish and post-commit completeness while delivering no assessment, recreating the silent-miss class `audit_runs._guideline_assessment_scan_obj` already flags as fail.
- **Proposed resolution**: Require non-empty content in the shared completeness helper (for example `stat().st_size > 0` or stripped read) for both `present` and artifact-present checks; add publish and run-log tests with a zero-byte regular file.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/report/run_log_commit.py:393-406
- **Concern**: Commit-time verify never receives consumer repo root. Scenario: Approach item 6 and `run_log_manifest.py` updates thread `repo_root` into `verify_run_log_completeness`, citing `run_log_commit._copy_tree_to_repo_after_completeness`, but `run_log_commit.py` is not in Files to modify/create. Pre-commit `src` lives under ephemeral `log_root`, so `_derive_consumer_repo_root_from_run_dir` often fails and the new guideline row is skipped at the commit gate.
- **Proposed resolution**: Add `### UPDATED: python/larch/report/run_log_commit.py` passing resolved `repo_root` into `verify_run_log_completeness`; keep derive-only fallback for audit callers without cwd context.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/report/test_run_logs.py
- **Concern**: Planned run-log tests can pass vacuously without guideline fixtures. Scenario: New `guideline-assessment` rows require `read_guidelines(repo_root).status == "present"` and an approved final-summary header. Existing design completeness tests use bare `final-summary.md` bodies and never seed `ARCHITECTURAL_GUIDELINES.md` at the derived repo root, so missing-assessment cases may never add the required row.
- **Proposed resolution**: Pin fixtures: write `## /design run <id>: approved` (or `: approved-partition`) into `final-summary.md`, place a valid `ARCHITECTURAL_GUIDELINES.md` at the derived consumer root, and assert the row appears before testing missing-artifact failure.

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step5c.py:610-645
- **Concern**: Touching `.completed/step-5c` still happens before the new `PUBLISH_REFUSE_REASON=missing-guideline-assessment` branch.. Scenario: A missing assessment refusal will still mark Step 5c complete, so Step 6 can run cleanup and the orchestrator loses the fail-closed state the plan asks for.
- **Proposed resolution**: Move the `.completed/step-5c` write after refusal handling, or explicitly remove the sentinel on this refusal path before returning.

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/design/design_log_publish_flow.py:50-56
- **Concern**: `.missing-guideline-assessment-warning` is only created, not cleared, so the new summary marker is sticky across retries.. Scenario: After a Return to Gate C retry successfully persists the assessment, the stale marker can still force the warning into `final-summary.md`, making a repaired run look incomplete.
- **Proposed resolution**: Delete the marker when completeness passes, or clear it before rerunning publish after Gate C so the summary prefix reflects the current state only.

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py
- **Concern**: Empty or whitespace-only architectural-guideline-assessment.md still satisfies the new presence check. Scenario: The plan treats present as a regular non-symlink file only. _verify_has_file in run_log_manifest.py is the same. A zero-byte file passes publish and post-commit completeness while audit_runs.py already fails empty assessments, so the measured silent-miss class survives through a technically regular file
- **Proposed resolution**: Require non-empty stripped content in _check_guideline_assessment_completeness and mirror the same rule in run-log verification (extend _verify_has_file or artifact_present_or_waived for slug guideline-assessment). Add a publish test with an empty assessment file that still expects refusal

### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_summary.py:649-666
- **Concern**: Plan prefixes the warning before the final-summary header. Scenario: The plan says to prefix the rendered summary with the missing-assessment warning, but docs/run-logs.md requires final-summary.md to begin with the `## /design run <run-id>: <outcome>` heading. Moving the header off line 1 can break existing consumers and the planned approved-outcome parser.
- **Proposed resolution**: Insert the warning immediately after the `## /design run ...` heading in normal and fallback summaries, and test that the header remains first.

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/run_log_manifest.py
- **Concern**: Run-log approved gating includes approved-partition. Scenario: Partition runs exit via decompose-panel before Gate C assessment persistence; requiring architectural-guideline-assessment.md when final-summary reads approved-partition will false-fail completeness on runs that never had a Gate C persist step
- **Proposed resolution**: Limit _design_run_approved and the guideline-assessment RequiredArtifact condition to terminal : approved only; exclude approved-partition unless partition runs are proven to reach persist-design-assessment

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py
- **Concern**: Presence check ignores empty assessment files. Scenario: The helper treats any regular non-symlink file as present; a zero-byte or whitespace-only architectural-guideline-assessment.md can pass publish and run-log verify while still matching the silent-miss failure mode
- **Proposed resolution**: Require non-empty stripped content in _check_guideline_assessment_completeness.present, aligned with persist_design_assessment whitespace rejection

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_step5c.py:642-644
- **Concern**: STEP5C_STATUS still unconditional validator-defects on publish_rc 4. Scenario: The plan says not to classify missing-guideline-assessment as validator-defects but does not specify the publish_rc 4 branch should emit a distinct STEP5C_STATUS or skip validator-defects; existing contract tests and bgjob logs will still label this refusal as validator-defects
- **Proposed resolution**: Branch publish_rc 4 on PUBLISH_REFUSE_REASON=missing-guideline-assessment to emit STEP5C_STATUS=missing-guideline-assessment (or gate-c-refusal) and add matching test_design_lifecycle coverage

### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_log_publish_flow.py:539-688
- **Concern**: Approved-partition publishes are not explicitly covered by the publish completeness gate. Scenario: The plan makes run-log verification treat approved-partition as approved, but the proposed publish helper says the artifact is required only when outcome is approved. The terminal split path publishes logs with outcome approved-partition, so a missing assessment can bypass the degraded warning/waiver path.
- **Proposed resolution**: Use an explicit approved outcome set containing approved and approved-partition in the completeness helper and degraded log-publish path. Add a focused approved-partition missing-artifact test.
