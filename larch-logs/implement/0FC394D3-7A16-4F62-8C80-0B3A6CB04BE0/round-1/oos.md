### FINDING_11: [OUT_OF_SCOPE] Future `rebase_and_rebump` tmpdir threading is not represented
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The plan mentions `rebase_and_rebump` tmpdir threading, but that symbol is not present yet; a future Python CI rebase entrypoint may omit tmpdir threading unless tracked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_12: [OUT_OF_SCOPE] Conflict CSV is not validated before future handoff emission
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Conflict paths are comma-joined without bash-equivalent validation. Future Phase 7 emission of `CONFLICT_FILES` could misroute malformed paths containing commas/newlines unless validation is added at the emit boundary or before join.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_14: [OUT_OF_SCOPE] Run-log commit may add unrelated PR noise
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: The branch includes a committed larch run-log flush alongside the feature commit, which may be unrelated review noise if not intended for the PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_15: [OUT_OF_SCOPE] Core library signal shape is otherwise sound
- **Reviewer(s)**: dyn-handoff-contract-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted the core `PrePushConflictHandoff` library shape is sound once parity gates and driver mapping are fixed; this is an out-of-scope positive observation rather than a separate corrective risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-handoff-contract-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] Plan text describes stale bump-gate contract
- **Reviewer(s)**: dyn-bump-gate-output.txt
- **Severity**: latent
- **Concern**: Plan and acceptance wording still describe CHANGELOG basenames and `LARCH_BUMP_FILES` as the bash contract, while current bash/docs use different rules. That can make reviewers or operators mistake Python divergence for intentional parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bump-gate-output.txt: Address the concern above.

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_3: [OUT_OF_SCOPE] CHANGELOG bump-path handling diverges from bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt, dyn-bump-gate-output.txt
- **Severity**: important
- **Concern**: Python treats `CHANGELOG`, `CHANGELOG.md`, and `CHANGELOG.rst` as bump/version paths, but bash’s non-bump-only gate does not. CHANGELOG-only conflict exhaustion can therefore stall in Python while bash would proceed to exit-4 conflict-resolution handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt, dyn-bump-gate-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] Missing bash parity harness for non-bump conflict classification
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt, dyn-bump-gate-output.txt
- **Severity**: latent
- **Concern**: There is no bash-sourced parity test covering Python `_conflicts_are_non_bump_only` / `_is_bump_path` against `ship_pr_vendor_conflict_csv_is_non_bump_only`, so env-var and CHANGELOG drift can recur without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt, dyn-bump-gate-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] Driver mapping swallows `PrePushConflictHandoff` metadata
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt
- **Severity**: latent
- **Concern**: Existing ship/finalize driver conversion treats `PrePushConflictHandoff` as generic `Stalled`, losing `conflict_files`, `resume_phase`, `caller_kind`, and related data needed for Phase 7 exit-4 conflict-resolution dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

