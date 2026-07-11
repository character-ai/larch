# Review Round 2

- Mode: `diff`
- 12 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_2: PR disposition validation binds the repository root to ambient cwd
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: `ensure_pr` and related PR mutation paths derive `repo_root` from `cwd` while consuming persisted run artifacts. Cwd drift can validate coverage and disposition against the wrong repository and produce an inconsistent issue-link kind.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_3: Commit-route coverage relay uses the wrong repository root
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-artifact-trust
- **Severity**: major
- **Concern**: `_relay_scope_coverage` and step-4 recovery use ambient `git rev-parse` rather than persisted implement-run state. Under cwd drift, recomputation can target a foreign checkout, overwrite coverage artifacts with foreign fingerprints, and relay incorrect `PLAN_COVERAGE_*` values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-artifact-trust: Address the concern above.


### FINDING_4: Stale snapshot handling mutates the repository
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: When the coder changes Git HEAD after snapshot creation, stale snapshot detection still invokes cleanup and restoration from the old pre-coder HEAD. The stale branch must abort before any restore, staging, or cleanup mutation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_6: Trusted atomic publication has an ancestor/root replacement race
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: `trusted_atomic_write` validates a root path and later reopens it by pathname. A same-UID process can replace the root or an ancestor with an attacker-controlled directory before publication, causing the write to escape the originally validated boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_7: Required consumer regression tests are missing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Plan-listed consumer test modules were not updated for hardened coverage, disposition, snapshot, PR, final-report, finalization, dispatch, and review-cleanup behavior. Invalid, absent, stale, unsafe, and compatibility artifact paths can regress without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_8: Dispatch recomputation failure lacks fail-closed coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: No direct test verifies that live coverage recomputation failure returns exit code 4 and emits no `PLAN_COVERAGE_*` relay keys. Advisory fallback or stale persisted coverage could otherwise be restored silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_9: Final-report coverage and persisted-root behavior is untested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Final-report behavior for absent, valid, and invalid coverage/disposition artifact sets is not covered, so invalid artifacts may render misleading empty summaries or raise uncaught `ShipError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_10: Snapshot cleanup and mode-selection regression tests are missing
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Review tests do not cover incomplete, unsafe, stale, or tampered snapshot sets, including valid full and `head_untracked` recovery paths. Cleanup or staging could mutate state despite invalid snapshot inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_11: Scope-disposition lifecycle coverage is incomplete
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: Tests cover only a narrow subset of partial or symlinked coverage cases. Live-input drift, unsafe manifest and baseline reads, repository-root handling, invalid-versus-absent dispositions, CLI behavior, and failed-publication cleanup remain unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


### FINDING_12: Trusted-I/O hostile-path and publication tests are incomplete
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The trusted-I/O test matrix omits required cases for FIFO or non-regular roots, dangling and ancestor symlinks, exclusive root creation, deterministic root reuse, interrupted or replacement races, descriptor revalidation, failed-publication cleanup, and legacy atomic-write compatibility.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_13: Snapshot consumers reopen validated head artifacts by pathname
- **Reviewer(s)**: dyn-dyn-artifact-trust
- **Severity**: major
- **Concern**: `_round_diff_base` and `_collect_round_stage_paths` recheck and reopen `pre-coder-head.txt` after snapshot validation using path-based operations. A replacement race can change the artifact between validation and use, affecting HEAD comparisons and staged paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-artifact-trust: Address the concern above.


### FINDING_14: Self-review staging lacks complete snapshot validation
- **Reviewer(s)**: dyn-dyn-artifact-trust
- **Severity**: major
- **Concern**: `_collect_self_review_stage_paths` checks only `pre-self-review-head.txt` and does not validate patch directories, patch-file containment and types, patch-set equality, or HEAD consistency before returning paths to stage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-artifact-trust: Address the concern above.
