### FINDING_1: Pre-push handoff must be gated away from postbump callers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `PrePushConflictHandoff` can be raised for all `rebase_and_push(..., allow_conflict_fix=True)` callers, including finalize/postbump paths where bash currently returns a plain rebase failure/stall without conflict-resolution handoff. The Python path needs an explicit handoff enablement guard used only by the CI-fix pre-push rebase entrypoint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Python bump gate ignores canonical `LARCH_VERSION_FILES`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt, dyn-bump-gate-output.txt
- **Severity**: important
- **Concern**: `_larch_bump_files()` reads only `LARCH_BUMP_FILES`, while bash treats `LARCH_VERSION_FILES` as canonical and falls back to deprecated `LARCH_BUMP_FILES`. Repos configured with only `LARCH_VERSION_FILES` can classify version-file conflicts differently in Python vs bash, causing spurious or missing `PrePushConflictHandoff`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt, dyn-bump-gate-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] CHANGELOG bump-path handling diverges from bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt, dyn-bump-gate-output.txt
- **Severity**: important
- **Concern**: Python treats `CHANGELOG`, `CHANGELOG.md`, and `CHANGELOG.rst` as bump/version paths, but bash’s non-bump-only gate does not. CHANGELOG-only conflict exhaustion can therefore stall in Python while bash would proceed to exit-4 conflict-resolution handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt, dyn-bump-gate-output.txt: Address the concern above.

### FINDING_4: Bump-path classification logic is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_is_bump_path` and `_deterministic_prepass` duplicate bump-path classification rules, so future edits can update one path and silently leave the other divergent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Missing bash parity harness for non-bump conflict classification
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt, dyn-bump-gate-output.txt
- **Severity**: latent
- **Concern**: There is no bash-sourced parity test covering Python `_conflicts_are_non_bump_only` / `_is_bump_path` against `ship_pr_vendor_conflict_csv_is_non_bump_only`, so env-var and CHANGELOG drift can recur without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt, dyn-bump-gate-output.txt: Address the concern above.

### FINDING_6: Missing test for `IMPLEMENT_TMPDIR` fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not cover the case where `tmpdir=None` and `IMPLEMENT_TMPDIR` is set. Callers relying on the environment fallback could regress without CI detecting flag placement or handoff behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Missing test for unconfigured handoff tmpdir
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests do not cover the branch where both `tmpdir` and `IMPLEMENT_TMPDIR` are absent. That path should raise plain `Stalled` with no handoff tokens or flag write.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Driver mapping swallows `PrePushConflictHandoff` metadata
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt
- **Severity**: latent
- **Concern**: Existing ship/finalize driver conversion treats `PrePushConflictHandoff` as generic `Stalled`, losing `conflict_files`, `resume_phase`, `caller_kind`, and related data needed for Phase 7 exit-4 conflict-resolution dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt: Address the concern above.

### FINDING_9: Bump-only tests lock in weak or wrong bump-path coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-bump-gate-output.txt
- **Severity**: nit
- **Concern**: Bump-only exhaustion tests rely on CHANGELOG behavior and do not cover all bash-recognized bump path classes such as `.claude-plugin/plugin.json`, `version.go`, `go.sum`, or env-listed version files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-bump-gate-output.txt: Address the concern above.

### FINDING_10: Handoff error tests use hardcoded phase/kind strings
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `python/test_errors.py` asserts hardcoded phase and caller-kind strings instead of config constants, so config renames could weaken the error-contract coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Future `rebase_and_rebump` tmpdir threading is not represented
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The plan mentions `rebase_and_rebump` tmpdir threading, but that symbol is not present yet; a future Python CI rebase entrypoint may omit tmpdir threading unless tracked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Conflict CSV is not validated before future handoff emission
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Conflict paths are comma-joined without bash-equivalent validation. Future Phase 7 emission of `CONFLICT_FILES` could misroute malformed paths containing commas/newlines unless validation is added at the emit boundary or before join.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Handoff flag path trusts uncanonicalized tmpdir
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_write_handoff_flag` uses `tmpdir` / `IMPLEMENT_TMPDIR` without canonicalizing or enforcing an expected session-root prefix, so a poisoned env var could write the sentinel outside the intended session directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Run-log commit may add unrelated PR noise
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: The branch includes a committed larch run-log flush alongside the feature commit, which may be unrelated review noise if not intended for the PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Core library signal shape is otherwise sound
- **Reviewer(s)**: dyn-handoff-contract-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted the core `PrePushConflictHandoff` library shape is sound once parity gates and driver mapping are fixed; this is an out-of-scope positive observation rather than a separate corrective risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-handoff-contract-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Plan text describes stale bump-gate contract
- **Reviewer(s)**: dyn-bump-gate-output.txt
- **Severity**: latent
- **Concern**: Plan and acceptance wording still describe CHANGELOG basenames and `LARCH_BUMP_FILES` as the bash contract, while current bash/docs use different rules. That can make reviewers or operators mistake Python divergence for intentional parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bump-gate-output.txt: Address the concern above.
