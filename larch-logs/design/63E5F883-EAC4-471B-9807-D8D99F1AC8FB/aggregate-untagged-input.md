### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/review/round_runner.py:1020 python/larch/review/review_and_fix.py:931 python/larch/review/snapshot.py:878-899
- **Concern**: Prior FINDING_1 fix is incomplete: Step 5 entry points still call _write_pre_coder_snapshot directly before apply_findings_with_coder. Scenario: The plan hardens only coder_runner._ensure_pre_coder_snapshot, but round_runner and review_and_fix mav-apply invoke _write_pre_coder_snapshot first. That helper always clears artifacts via _clear_stale_pre_coder_snapshot_artifacts and rewrites the root. A present-invalid snapshot is therefore destroyed and replaced before the complete validator runs, recreating the exact rewrite-and-mutate failure FINDING_1 targets. Fail-closed validation in coder_runner cannot recover evidence already cleared upstream.
- **Proposed resolution**: Add ### UPDATED: python/larch/review/round_runner.py and ### UPDATED: python/larch/review/review_and_fix.py. Replace direct _write_pre_coder_snapshot calls with the shared snapshot-preparation entry that runs the complete validator, creates only on wholly absent state, and maps present-invalid failures to the existing bounded coder failure envelope. Either make _write_pre_coder_snapshot creation-only and unreachable on present roots, or guard it inside the validator module. Extend test_review_and_fix.py or add round_runner coverage for the main Step 5 loop and mav-apply paths.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_and_fix.py:931
- **Concern**: The `mav-apply` path writes the pre-coder snapshot directly before entering `apply_findings_with_coder`, but `review_and_fix.py` is absent from the production migration files.. Scenario: With a partial, unsafe, or stale snapshot root already present, `_write_pre_coder_snapshot` can clear or overwrite the evidence before the planned complete validator runs. This still permits the exact rewrite-before-rejection failure the change is intended to prevent.
- **Proposed resolution**: Route the `mav-apply` path through the complete snapshot preparation/validation helper, or remove this direct write and make `apply_findings_with_coder` own validation and creation. Ensure existing present-invalid state fails before any snapshot mutation.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_and_fix.py:931 and python/larch/review/round_runner.py:1020
- **Concern**: Prior FINDING_1 fix is incomplete: production still calls `_write_pre_coder_snapshot` outside the planned validator gate. Scenario: Those paths run before `apply_findings_with_coder`; `_write_pre_coder_snapshot` always calls `_clear_stale_pre_coder_snapshot_artifacts`, so present-but-partial or unsafe snapshot roots are still cleared and rewritten while `_snapshot_mode` would classify them as `missing`
- **Proposed resolution**: Make `_write_pre_coder_snapshot` run the complete validator first and write only on wholly absent state, or replace both call sites with the validator-backed preparation helper; do not rely on hardening only `_ensure_pre_coder_snapshot` in `coder_runner.py`

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/scope_disposition.py:558-564
- **Concern**: Prior FINDING_6 fix is incomplete: `load_disposition` maps present-invalid disposition files to absent. Scenario: When `disposition_path` exists but `trusted_file_present` is false (symlinked or unsafe), `load_disposition` returns `None`; `disposition_link_kind` then defaults to `closes` and deferred inventory omits disposition context instead of raising
- **Proposed resolution**: Raise `ShipError` on present-but-untrusted disposition artifacts inside `load_disposition`, or have the shared declared-context wrapper validate disposition presence before calling it and forbid the soft-`None` path

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/round_runner.py:1020; python/larch/review/review_and_fix.py:931
- **Concern**: Direct production callers still invoke `_write_pre_coder_snapshot` without the complete validator. Scenario: An existing partial or unsafe snapshot can be cleared and rewritten before `coder_runner` validates it, so the planned fail-closed contract is bypassed in normal round and `mav-apply` execution paths
- **Proposed resolution**: Route every production snapshot-creation call through the complete prepare-or-validate helper, or make `_write_pre_coder_snapshot` reject any non-wholly-absent state before clearing or writing

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/scope_disposition.py:660-689; python/larch/git/pr.py:110-145; python/larch/git/pr_body.py:419-432
- **Concern**: Disposition-only consumers do not accept or propagate the explicit `manifest_path` used by the mutation gate. Scenario: With a non-default manifest, mutation validation can authenticate one manifest while PR links and deferred inventory resolve another or treat coverage as absent, producing an incorrect `part-of` link or missing inventory
- **Proposed resolution**: Add `manifest_path` to the shared disposition-only consumer APIs and pass the caller's explicit manifest through PR creation/update and body-rendering paths; use the persisted manifest where finalize and report consumers require it

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/round_runner.py:1020
- **Concern**: Step 5 still calls `_write_pre_coder_snapshot` directly, so the planned `_ensure_pre_coder_snapshot` gate in `coder_runner.py` does not cover the main review loop. Scenario: The primary `/implement` Step 5 path writes snapshots from `round_runner.py` (and `review_and_fix.py` mav-apply) via `_write_pre_coder_snapshot`, which always runs `_clear_stale_pre_coder_snapshot_artifacts` with no wholly-absent check. A present-but-partial or unsafe snapshot can be cleared and rewritten before `apply_findings_with_coder` runs, which leaves FINDING_1 mitigation incomplete
- **Proposed resolution**: Harden `_write_pre_coder_snapshot` in `snapshot.py` to run the complete validator and refuse writes unless wholly absent, or add `### UPDATED:` entries for `round_runner.py` and `review_and_fix.py` to call the validator-gated entry point instead; add a focused test that a partial snapshot on the round-runner path fails before coder launch and leaves repo state unchanged

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/scope_disposition.py:563-564
- **Concern**: [ALREADY_ADDRESSED] Shared invalid-present hardening does not name `load_disposition`, which still maps present-but-unsafe disposition files to `None`. Scenario: `load_disposition` returns `None` when a disposition file exists but fails `trusted_file_present`. `disposition_link_kind` then defaults to `closes`, and `validate_disposition_for_ship` reports `scope-disposition-missing` instead of invalid-present. Wrapper-only hardening can miss callers that still use `load_disposition` directly, including finalize teardown and final-report composition
- **Proposed resolution**: Make the plan explicitly require `load_disposition` (or one shared loader used by every consumer) to raise on present-invalid disposition artifacts, not only the three named wrapper functions; extend `test_scope_disposition.py` or the planned consumer tests to assert symlinked or partial disposition files raise rather than returning `None`

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/git/pr_body.py:396-432
- **Concern**: Prior accepted manifest-context fix remains incomplete because the plan adds no production PR-body path for passing an explicit manifest to disposition consumers. Scenario: `compose_pr_body` accepts only `implement_tmpdir`; with an explicit manifest and no valid tmpdir, both disposition helpers see no declared context and return empty inventory or `closes` instead of failing closed. The planned manifest-only PR-body test cannot exercise the required production contract.
- **Proposed resolution**: Add `python/larch/git/pr_body.py` to the firm changes. Give `compose_pr_body` an optional `manifest_path`, pass it to both disposition helpers, extend those helper signatures, and thread `RunContext.manifest_path` from the ship caller.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/round_runner.py:1020-1021
- **Concern**: The plan hardens snapshot creation in coder_runner but leaves round_runner and mav-apply calling _write_pre_coder_snapshot directly before apply_findings_with_coder.. Scenario: round_runner and review_and_fix mav-apply invoke _write_pre_coder_snapshot, which unconditionally clears the snapshot root via _clear_stale_pre_coder_snapshot_artifacts, before coder_runner can run the complete validator. A present-invalid snapshot is rewritten instead of failing closed, so FINDING_1 remains incomplete on the main Step 5 coder path.
- **Proposed resolution**: Add ### UPDATED: python/larch/review/round_runner.py and ### UPDATED: python/larch/review/review_and_fix.py. Remove the direct _write_pre_coder_snapshot calls at round_runner.py:1020 and review_and_fix.py:931. Let apply_findings_with_coder own validator-first preparation, or route both sites through the same shared snapshot-preparation helper that validates wholly absent state before any write.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/review/snapshot.py:878-881
- **Concern**: The plan forbids clearing invalid-present snapshot roots but does not bind _write_pre_coder_snapshot to that rule.. Scenario: _write_pre_coder_snapshot always calls _clear_stale_pre_coder_snapshot_artifacts before writing. Any direct caller, including round_runner and mav-apply, can erase invalid snapshot evidence even after snapshot.py adds a complete validator used only from _ensure_pre_coder_snapshot.
- **Proposed resolution**: In snapshot.py, gate _write_pre_coder_snapshot behind the complete validator so it raises on present-invalid state and writes only on wholly absent state. Restrict production callers to the validator-backed preparation API, or make _write_pre_coder_snapshot an internal helper unreachable from round_runner and review_and_fix. schema_version scope severity focus_area location what scenario_or_breakage suggested_fix

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/round_runner.py:1020-1021
- **Concern**: The plan hardens snapshot creation in coder_runner but leaves round_runner and mav-apply calling _write_pre_coder_snapshot directly before apply_findings_with_coder.. Scenario: round_runner and review_and_fix mav-apply invoke _write_pre_coder_snapshot, which unconditionally clears the snapshot root via _clear_stale_pre_coder_snapshot_artifacts, before coder_runner can run the complete validator. A present-invalid snapshot is rewritten instead of failing closed, so FINDING_1 remains incomplete on the main Step 5 coder path.
- **Proposed resolution**: Add ### UPDATED: python/larch/review/round_runner.py and ### UPDATED: python/larch/review/review_and_fix.py. Remove the direct _write_pre_coder_snapshot calls at round_runner.py:1020 and review_and_fix.py:931. Let apply_findings_with_coder own validator-first preparation, or route both sites through the same shared snapshot-preparation helper that validates wholly absent state before any write.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/review/snapshot.py:878-881
- **Concern**: The plan forbids clearing invalid-present snapshot roots but does not bind _write_pre_coder_snapshot to that rule.. Scenario: _write_pre_coder_snapshot always calls _clear_stale_pre_coder_snapshot_artifacts before writing. Any direct caller, including round_runner and mav-apply, can erase invalid snapshot evidence even after snapshot.py adds a complete validator used only from _ensure_pre_coder_snapshot.
- **Proposed resolution**: In snapshot.py, gate _write_pre_coder_snapshot behind the complete validator so it raises on present-invalid state and writes only on wholly absent state. Restrict production callers to the validator-backed preparation API, or make _write_pre_coder_snapshot an internal helper unreachable from round_runner and review_and_fix.

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:39-47,55-59
- **Concern**: The snapshot contract does not distinguish immutable pre-coder artifacts from attempt artifacts that the lifecycle intentionally creates or replaces. Scenario: Attempt capture writes `attempt-pre-tracked-paths.txt`, `attempt-pre-untracked-paths.txt`, and `attempt-pre-path-diffs` inside the validated snapshot root. A later complete-root revalidation may reject these as unexpected or changed artifacts, while accepting all root changes would weaken tamper detection. Failed-attempt cleanup and subsequent attempts can therefore fail on artifacts created by the feature itself.
- **Proposed resolution**: Define separate validation rules for immutable pre-coder artifacts and mutable attempt artifacts. Authenticate each attempt artifact set after writing it and return an updated validated record, then require cleanup and staging to validate that exact attempt record while still rejecting changes to the pre-coder set.
