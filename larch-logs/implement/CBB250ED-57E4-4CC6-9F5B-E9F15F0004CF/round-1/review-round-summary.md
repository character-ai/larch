# Review Round 1

- Mode: `diff`
- 11 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Snapshot mode accepts incomplete or tampered artifacts
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-artifact-trust, dyn-dyn-artifact-trust-codex
- **Severity**: major
- **Concern**: `_snapshot_mode` classifies snapshots as complete based primarily on the presence of top-level marker files. It does not validate the required patch directories and per-path patch files, regular-file and containment properties, patch validity, or HEAD consistency. Cleanup, restoration, comparison, and staging can therefore operate on incomplete or tampered evidence, potentially restoring or staging incorrect paths or erasing pre-existing changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Add a complete validator and require cleanup, restore, comparison, diff-base, and staging paths to consume its validated mode and artifacts.
  - From cursor-specialist-edge-cases: Require trusted patch artifacts and HEAD consistency before returning full mode.
  - From codex-specialist-edge-cases: Implement one complete trusted validator and make all cleanup, restoration, comparison, and staging consumers use its validated mode and artifacts.
  - From dyn-dyn-artifact-trust: Extend mode detection to validate the full artifact set (including patch directories and HEAD agreement) before returning `full`/`head_untracked`, and abort before any `git restore`/patch application when required artifacts are missing or untrusted.
  - From dyn-dyn-artifact-trust-codex: replace `_snapshot_mode` with a complete validator that verifies every inventory entry has both contained, no-follow regular patch artifacts (and validates their patch content) before returning `full`; make cleanup reject any incomplete snapshot before issuing restore or apply commands.


### FINDING_2: `post-coder-head.txt` is written through an unsafe path
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-artifact-trust, dyn-dyn-artifact-trust-codex
- **Severity**: major
- **Concern**: The `post-coder-head.txt` writers in `round_runner.py` and `review_and_fix.py` still unlink and recreate the file through an ordinary path-based writer. A same-UID symlink or replacement race can redirect the write outside the round directory, while later consumers may read an unsafe or non-regular artifact as a diff base.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Use a snapshot trusted-write helper for post-coder-head.txt in round_runner.py and review_and_fix.py, with no-follow random temp creation, final validation, and permission hardening.
  - From codex-specialist-correctness: Route both writers through one trusted snapshot helper using trusted_atomic_write, final-path validation, and 0444 hardening.
  - From cursor-specialist-edge-cases: Route the write through snapshot trusted_atomic_write with final-path revalidation and keep post-write chmod hardening.
  - From codex-specialist-edge-cases: Route both call sites through one snapshot trusted writer that safely publishes, validates the final artifact, and reapplies read-only permissions.
  - From dyn-dyn-artifact-trust: Route `round_runner.py` and `review_and_fix.py` mav-apply `post-coder-head.txt` creation through `snapshot._write_text` (or an equivalent trusted helper bound to `round_dir`), reject symlinked parents with `trusted_file_present`, and add regression tests for symlinked destinations.
  - From dyn-dyn-artifact-trust-codex: expose a snapshot-owned trusted write/read helper and route both writers through it, including final-path validation and read-only permission hardening; have diff-base and structural consumers use the same validator-backed reader.


### FINDING_4: `record_disposition` trusts caller-supplied stale coverage
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: `record_disposition` persists a caller-provided coverage object without always revalidating it against the current plan, baseline, manifest, HEAD, and worktree. Coverage computed earlier can become stale before persistence, producing an invalid disposition fingerprint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Always load live coverage inside record_disposition and reject a supplied coverage object that differs, or remove the bypass parameter.


### FINDING_5: `trusted_atomic_write` has an ancestor-swap publication race
- **Reviewer(s)**: codex-specialist-edge-cases, dyn-dyn-artifact-trust, dyn-dyn-artifact-trust-codex
- **Severity**: major
- **Concern**: `trusted_atomic_write` validates pathname containment before using path-based replacement. A same-UID process can swap a validated parent directory for a symlink between validation and replacement, causing the temporary file to be published outside the trusted root. Post-write validation detects the escape only after the external write may already have occurred.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Use stable directory descriptors and descriptor-relative creation and replacement, or revalidate directory identity immediately before a non-escapable descriptor-relative publish.
  - From dyn-dyn-artifact-trust: Publish through an `os.replace`/`renameat` path that refuses symlink destinations (or re-open the destination with `O_NOFOLLOW` immediately before rename), and fail closed without leaving a trusted completion artifact when post-replace validation fails.
  - From dyn-dyn-artifact-trust-codex: perform creation and publication relative to a validated directory descriptor (for example, `openat`/`renameat` semantics with no-follow checks), or otherwise retain and operate through an opened trusted parent directory so an ancestor swap cannot redirect the publish.


### FINDING_6: Live validation uses the wrong repository root under cwd drift
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-artifact-trust
- **Severity**: minor
- **Concern**: Teardown and PR-body live validation resolve `repo_root` from the current working directory instead of persisted run state. Cwd drift can bind coverage and disposition validation to the wrong repository while consuming artifacts from the actual run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Use progress_file.resolve_persisted_repo_root with the same fallback pattern as final_report
  - From dyn-dyn-artifact-trust: Resolve `repo_root` from persisted run state (same source as `final_report.py` / ship driver `repo_root`) and thread that value through `compose_pr_body`, `disposition_link_kind`, and finalize teardown; fail closed when persisted root is unavailable but coverage artifacts are present.


### FINDING_7: Plan-required consumer regression tests are missing
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Several production modules changed without corresponding updates to the plan-listed consumer test modules. Invalid coverage, disposition, snapshot, PR, final-report, and teardown behavior can regress without CI coverage at the consumer boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add the plan-listed regression tests to test_implement_dispatch.py, test_final_report.py, test_pr.py, test_pr_body.py, test_finalize.py, and test_review_and_fix.py.
  - From codex-specialist-testing: Add focused tests in every plan-named consumer test module for absent partial unsafe stale malformed and fingerprint-mismatched artifacts.


### FINDING_8: Missing test for fail-closed dispatch coverage recomputation
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: No test asserts that commit routing returns code 4 and avoids relaying stale persisted coverage when recomputation fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a test with persisted non-required coverage and forced compute_and_write_coverage failure; expect return code 4 and no stale relay.


### FINDING_9: Missing incomplete and unsafe snapshot cleanup tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: `_snapshot_mode` now raises on incomplete snapshots, but review regression tests do not cover incomplete, symlinked, or stale snapshot sets before cleanup performs restore or staging operations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add test_review_and_fix.py cases for incomplete, symlinked, and stale snapshot sets before git restore or staging.


### FINDING_10: Missing finalize teardown tests for invalid coverage and disposition
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Finalize teardown now live-validates disposition without tests covering valid partial disposition, absent coverage, or invalid present coverage. Corrupt artifacts may cause successful runs to abort through an uncaught `ShipError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add finalize teardown tests for valid proceed-partial, absent coverage, and invalid present coverage; define expected failure surface.


### FINDING_11: Trusted-I/O regression coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Trusted-I/O tests do not cover required ancestor and dangling symlinks, FIFOs, directories, non-regular files, exclusive root creation, root reuse, replacement races, and failed-publication cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Expand test_larch_io.py per the plan trusted-I/O checklist.
  - From codex-specialist-testing: Add focused tests for every required unsafe-path race deterministic-root reuse and cleanup case.


### FINDING_12: Scope-disposition test matrix is incomplete
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Scope-disposition tests cover only a subset of the planned negative and integration paths. Live drift, CLI repository-root handling, and invalid-versus-absent disposition behavior remain unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add live-mismatch, record_disposition CLI, and disposition wrapper tests from the plan.
