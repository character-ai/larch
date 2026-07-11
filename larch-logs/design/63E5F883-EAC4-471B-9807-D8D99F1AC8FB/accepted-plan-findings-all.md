### FINDING_1: Partial snapshots are rewritten before complete validation
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Artifact Trust Boundaries, Codex-dyn-Artifact Trust Boundaries
- **Severity**: major
- **Concern**: `_snapshot_mode` classifies many present-but-partial or unsafe snapshot roots as `missing`. `_ensure_pre_coder_snapshot` then clears and rewrites those artifacts before the complete validator runs, destroying evidence of invalid state and potentially mutating the repository before fail-closed rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make `_ensure_pre_coder_snapshot` distinguish wholly absent from present-invalid state through the complete validator. Create a snapshot only when wholly absent; propagate present-invalid failure before clearing or rewriting artifacts.
  - From Cursor-Innovation: Run the complete validator before any write; only call `_write_pre_coder_snapshot` when the validator reports wholly absent; raise on partial or unsafe present sets without clearing artifacts first
  - From Codex-Innovation: Make snapshot preparation distinguish wholly absent roots from present roots. Invoke the complete validator before clearing any present artifact set, and only create a new snapshot when the entire root is absent
  - From Cursor-Pragmatic: Run the complete validator first; call `_ensure_pre_coder_snapshot` only when the validator reports a wholly absent snapshot; raise on present-but-invalid; update `_ensure_pre_coder_snapshot` in snapshot.py to use the same absent/invalid distinction
  - From Codex-Pragmatic: Make the complete validator classify the snapshot before `_ensure_pre_coder_snapshot`. Create a snapshot only for the wholly absent result, then validate the new snapshot before use.
  - From Cursor-Requirements: Run a pre-coder validator first (or teach _ensure_pre_coder_snapshot to fail closed on partial-present sets); only create a fresh snapshot when validation reports wholly absent; then reuse the validated mode and HEAD for dispatch and cleanup
  - From Cursor-dyn-Artifact Trust Boundaries: Run complete validation first; only call _write_pre_coder_snapshot on wholly absent roots; teach _ensure_pre_coder_snapshot to refuse existing partial/untrusted snap_dir contents instead of classifying them as missing.
  - From Codex-dyn-Artifact Trust Boundaries: Validate an existing snapshot root and artifact set before any write or cleanup. Only create a snapshot when the snapshot root is wholly absent. Make `_ensure_pre_coder_snapshot` use the complete validator or an explicit absent-state result instead of `_snapshot_mode`.


### FINDING_2: Downstream cleanup and staging reclassify snapshots after startup validation
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Artifact Trust Boundaries, Codex-dyn-Artifact Trust Boundaries
- **Severity**: major
- **Concern**: Cleanup, diff-base, snapshot-head, and staging helpers continue to reread artifacts and call `_snapshot_mode` after coder startup validation. Changed, partial, or replaced artifacts can therefore produce a different mode or HEAD, trigger incorrect cleanup, or omit staging evidence instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the validator return a validated snapshot object and pass it through cleanup and staging helpers, or require those helpers to invoke the complete validator and abort before any mutation when validation fails. Remove heuristic classification from every production decision path, not only `coder_runner.py`.
  - From Cursor-Innovation: Thread validated mode and pre_head from coder_runner into cleanup (or make cleanup call the complete validator and fail closed); stop using _snapshot_mode inside _cleanup_failed_coder_attempt
  - From Codex-Innovation: Route the validated mode and HEAD through cleanup, staging, and snapshot-head helpers, or centralize those operations behind one validated snapshot object; remove all production `_snapshot_mode` decisions except wholly-absent snapshot creation
  - From Cursor-Pragmatic: Pass validated mode/pre_head into cleanup helpers or have `_cleanup_failed_coder_attempt` call the complete validator before mutating the repo
  - From Cursor-Requirements: Add a snapshot.py change (or extend the coder_runner step) to pass validated mode/HEAD into cleanup helpers instead of reclassifying with _snapshot_mode
  - From Cursor-dyn-Artifact Trust Boundaries: Revalidate the complete snapshot immediately before each post-coder cleanup or staging consumer, or pass immutable validated artifact contents through those decisions. Stop without repository mutation if revalidation fails.
  - From Codex-dyn-Artifact Trust Boundaries: Pass the validated snapshot record to cleanup, attempt capture, diff-base, and staging helpers, or make those helpers consume a shared immutable validated record and reject any artifact change rather than reclassifying with `_snapshot_mode`.


### FINDING_3: Manifest-only context has no defined trusted artifact root or failure contract
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-Artifact Trust Boundaries, Codex-dyn-Artifact Trust Boundaries
- **Severity**: major
- **Concern**: An explicit `manifest_path` is treated as declared context, but when `tmpdir` and `IMPLEMENT_TMPDIR` are absent or invalid, the implementation has no defined trusted root for coverage, disposition, and gate validation. The current early return can bypass validation, while deriving a root from the manifest or requiring a tmpdir has not been resolved consistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Define deterministic manifest-only root resolution for each supported manifest location, validate that root before artifact access, and reject explicit manifests outside those layouts. Alternatively, require an accompanying tmpdir and revise the manifest-only requirement and tests.
  - From Codex-Innovation: Define and implement the trusted context-root resolution for manifest-only calls, update every production caller to pass `manifest_path` where available, and specify the failure behavior when a manifest exists without a valid artifact directory before running disposition validation
  - From Codex-Pragmatic: Specify that manifest-only context without a tmpdir fails before mutation. Test disposition validation only when a valid tmpdir accompanies the explicit manifest.
  - From Codex-Requirements: Specify that manifest-only context fails closed when no effective tmpdir exists. Update the manifest-only test requirement to assert refusal before mutation rather than disposition validation
  - From Cursor-dyn-Artifact Trust Boundaries: Evaluate manifest_path (and derive tmpdir from its parent when appropriate) before the standalone no-op return; raise ShipError when manifest declares context but tmpdir/env is missing or invalid.
  - From Codex-dyn-Artifact Trust Boundaries: Define the trusted context root for an explicit manifest, or require and validate an associated tmpdir. Reject a missing, non-directory, symlinked, or otherwise unsafe declared root before resolving or validating gate artifacts.


### FINDING_4: Tests still monkeypatch the removed `_snapshot_mode` symbol
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Removing or relocating `coder_runner._snapshot_mode` without updating dependent tests will cause collection or runtime failures in `test_external_dispatch.py` and `test_review_pipeline.py`, in addition to the already planned review-fix test updates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Those tests patch coder_runner._snapshot_mode; after the import is removed the patches fail at collection or runtime and CI breaks Add ### UPDATED entries for both test modules: patch the new validator entry point or snapshot helper instead of _snapshot_mode
  - From Cursor-Pragmatic: Add `### UPDATED:` entries for python/tests/agents/test_external_dispatch.py and python/tests/review/test_review_pipeline.py (patch the new validator entry point instead of `_snapshot_mode`)
  - From Cursor-Requirements: List ### UPDATED: python/tests/agents/test_external_dispatch.py and ### UPDATED: python/tests/review/test_review_pipeline.py, repointing mocks to the new complete validator entry point


### FINDING_6: Disposition-only consumers can fail open outside the mutation gate
- **Reviewer(s)**: Cursor-dyn-Artifact Trust Boundaries
- **Severity**: major
- **Concern**: `disposition_link_kind` and `disposition_deferred_inventory` directly load coverage or disposition artifacts without the hardened declared-context and invalid-present checks. Partial, symlinked, stale, or fingerprint-mismatched artifacts can therefore influence PR-body links, deferred inventory, teardown, or `[DESIGNED]` handling without raising.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Artifact Trust Boundaries: Extend scope_disposition.py beyond require_pr_mutation: shared declared-context + invalid-present validation used by disposition_link_kind and disposition_deferred_inventory (reject disposition-only, symlinked, partial, stale, or fingerprint-mismatched sets with ShipError). Align finalize and pr_body tests with that shared path.


### FINDING_7: Final-report coverage summaries are not included in invalid-present hardening
- **Reviewer(s)**: Cursor-dyn-Artifact Trust Boundaries
- **Severity**: major
- **Concern**: `_plan_coverage_summary_line` can return an empty string when `load_live_coverage` returns `None`, even when gate-relevant coverage or disposition artifacts are present but invalid. Updating only tests leaves the production report path inconsistent with the promised fail-closed behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Artifact Trust Boundaries: Add ### UPDATED: python/larch/report/final_report.py (or route through the shared scope_disposition validator) so invalid-present artifacts raise through the report path instead of rendering empty coverage.


### FINDING_1: Snapshot validation is bypassed by direct production callers
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The planned snapshot hardening only covers `coder_runner.py`, while the main Step 5 and `mav-apply` paths still call `_write_pre_coder_snapshot` directly. That helper clears and rewrites present-but-invalid snapshot roots before the complete validator runs, so invalid evidence can still be destroyed instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/larch/review/round_runner.py and ### UPDATED: python/larch/review/review_and_fix.py. Replace direct _write_pre_coder_snapshot calls with the shared snapshot-preparation entry that runs the complete validator, creates only on wholly absent state, and maps present-invalid failures to the existing bounded coder failure envelope. Either make _write_pre_coder_snapshot creation-only and unreachable on present roots, or guard it inside the validator module. Extend test_review_and_fix.py or add round_runner coverage for the main Step 5 loop and mav-apply paths.
  - From Codex-Arch: Route the `mav-apply` path through the complete snapshot preparation/validation helper, or remove this direct write and make `apply_findings_with_coder` own validation and creation. Ensure existing present-invalid state fails before any snapshot mutation.
  - From Cursor-Innovation: Make `_write_pre_coder_snapshot` run the complete validator first and write only on wholly absent state, or replace both call sites with the validator-backed preparation helper; do not rely on hardening only `_ensure_pre_coder_snapshot` in `coder_runner.py`
  - From Codex-Innovation: Route every production snapshot-creation call through the complete prepare-or-validate helper, or make `_write_pre_coder_snapshot` reject any non-wholly-absent state before clearing or writing
  - From Cursor-Pragmatic: Harden `_write_pre_coder_snapshot` in `snapshot.py` to run the complete validator and refuse writes unless wholly absent, or add `### UPDATED:` entries for `round_runner.py` and `review_and_fix.py` to call the validator-gated entry point instead; add a focused test that a partial snapshot on the round-runner path fails before coder launch and leaves repo state unchanged
  - From Cursor-Requirements: Add ### UPDATED: python/larch/review/round_runner.py and ### UPDATED: python/larch/review/review_and_fix.py. Remove the direct _write_pre_coder_snapshot calls at round_runner.py:1020 and review_and_fix.py:931. Let apply_findings_with_coder own validator-first preparation, or route both sites through the same shared snapshot-preparation helper that validates wholly absent state before any write.
  - From Cursor-Requirements: In snapshot.py, gate _write_pre_coder_snapshot behind the complete validator so it raises on present-invalid state and writes only on wholly absent state. Restrict production callers to the validator-backed preparation API, or make _write_pre_coder_snapshot an internal helper unreachable from round_runner and review_and_fix.


### FINDING_2: Present-invalid disposition artifacts are softened to missing
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `load_disposition` treats an existing but untrusted disposition artifact as absent by returning `None`. Downstream consumers can therefore default to `closes` or report a missing disposition instead of rejecting invalid-present state, including callers that bypass wrapper-level validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Raise `ShipError` on present-but-untrusted disposition artifacts inside `load_disposition`, or have the shared declared-context wrapper validate disposition presence before calling it and forbid the soft-`None` path
  - From Cursor-Pragmatic: Make the plan explicitly require `load_disposition` (or one shared loader used by every consumer) to raise on present-invalid disposition artifacts, not only the three named wrapper functions; extend `test_scope_disposition.py` or the planned consumer tests to assert symlinked or partial disposition files raise rather than returning `None`


### FINDING_3: Explicit manifest context is not propagated to disposition-only consumers
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: major
- **Concern**: Disposition-only consumers and PR-body composition do not consistently accept and propagate the caller’s explicit `manifest_path`. With a non-default manifest, validation can authenticate one manifest while PR links, deferred inventory, or body rendering resolve another or silently omit context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add `manifest_path` to the shared disposition-only consumer APIs and pass the caller's explicit manifest through PR creation/update and body-rendering paths; use the persisted manifest where finalize and report consumers require it
  - From Codex-Pragmatic: Add `python/larch/git/pr_body.py` to the firm changes. Give `compose_pr_body` an optional `manifest_path`, pass it to both disposition helpers, extend those helper signatures, and thread `RunContext.manifest_path` from the ship caller.


