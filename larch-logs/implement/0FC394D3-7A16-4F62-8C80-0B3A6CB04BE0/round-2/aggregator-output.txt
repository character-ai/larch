### FINDING_1: CHANGELOG conflicts are bump-classified in Python but not bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-bump-classifier-output.txt, cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_is_bump_path` treats `CHANGELOG.md`, `CHANGELOG.rst`, and bare `CHANGELOG` as bump/version paths, suppressing pre-push conflict handoff for CHANGELOG-only conflicts. Bash `ship_pr_vendor_conflict_csv_is_non_bump_only` does not classify CHANGELOG files this way, so bash can hand off while Python stalls without the handoff flag. This creates bash-fidelity and Phase 7 routing risk; if intentional, it needs explicit documentation and parity coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.
  - From dyn-bump-classifier-output.txt: Address the concern above.
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Bump and mixed conflict tests do not exercise the enabled handoff gate
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bump-classifier-output.txt
- **Severity**: important
- **Concern**: Existing bump-only and mixed-conflict exhaustion tests omit `enable_pre_push_handoff=True`, so they only prove plain `Stalled` when handoff is disabled. The production path from `ship.py` enables handoff, leaving a regression hole where bump or mixed conflicts could incorrectly raise `PrePushConflictHandoff` or write the flag without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bump-classifier-output.txt: Address the concern above.

### FINDING_3: Site-2 resolved-conflict path lacks enabled-handoff regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The site-2 test does not enable handoff, so a future change could emit `PrePushConflictHandoff` after a winning recovery tier without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: No in-scope bash parity harness covers non-bump conflict classification
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Python’s non-bump conflict classification can drift from bash `ship_pr_vendor_conflict_csv_is_non_bump_only` without CI detection, as shown by the CHANGELOG mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: Ship driver loses pre-push handoff metadata at the goto_rebase boundary
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `PrePushConflictHandoff` is a `Stalled` subclass, so `_error_to_result` collapses it to generic `Outcome.STALLED`. The goto-rebase path writes the flag but does not preserve `conflict_files`, `resume_phase`, `caller_kind`, or equivalent state/JSON metadata needed by orchestration to dispatch conflict resolution. This creates a flag-only partial handoff that is not recoverable from driver outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_6: Handoff flag write trusts IMPLEMENT_TMPDIR without allowed-root validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_write_handoff_flag` can fall back to `IMPLEMENT_TMPDIR` without applying `ship.py`’s allowed-root validation. A library caller or harness with `enable_pre_push_handoff=True` and no explicit `tmpdir` could be steered into writing the handoff flag outside the intended session tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Legacy LARCH_BUMP_FILES fallback lacks bash-style warning
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Python silently falls back to the legacy `LARCH_BUMP_FILES` alias, while bash emits a deprecation warning. This can make cross-path debugging harder for operators using legacy environment configuration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Python waterfall short-circuit semantics may differ from bash tier iteration
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Python `run_waterfall` short-circuit behavior may attempt fewer fixer tiers than bash `run_recovery_waterfall` for the same conflict set, changing when handoff fires. The reviewer marked this pre-existing and relevant only if strict tier-count parity is required at Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Python CI monitor omits bash CI-fix rebase loop
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: Python intentionally omits bash’s CI-fix `run_rebase_rebump` / `CI_FIX_REBASE_PENDING` loop, so the new handoff is not exercised on that bash call site. The reviewer marked this as pre-existing broader bash/Python divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Postbump rebase path does not enable pre-push handoff
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: Postbump `rebase_and_push` does not pass `enable_pre_push_handoff=True`, matching an accepted bash degradation where postbump conflicts stall without conflict-resolution handoff. The reviewer marked this as no new regression from the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.

### FINDING_11: LARCH bump-file parsing uses os.pathsep instead of documented colon separator
- **Reviewer(s)**: dyn-bump-classifier-output.txt
- **Severity**: latent
- **Concern**: `_larch_bump_files()` splits `LARCH_VERSION_FILES` / `LARCH_BUMP_FILES` on `os.pathsep`. This matches bash on Unix but would accept semicolon-delimited lists on Windows, diverging from the documented colon-only bash contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bump-classifier-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Plan text still lists CHANGELOG files as bump paths
- **Reviewer(s)**: dyn-bump-classifier-output.txt
- **Severity**: nit
- **Concern**: Issue/plan text still lists CHANGELOG files as bump/version paths, which predates current bash behavior. The reviewer marked this as documentation drift outside the runtime diff, aside from the Python mismatch already captured above.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bump-classifier-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Bash-sourced parity harness for non-bump classification is absent
- **Reviewer(s)**: dyn-bump-classifier-output.txt
- **Severity**: latent
- **Concern**: No bash-sourced parity harness covers `ship_pr_vendor_conflict_csv_is_non_bump_only`. The reviewer marked a future parity test as useful recurrence prevention but outside this diff’s scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bump-classifier-output.txt: Address the concern above.

### FINDING_14: Public enable_pre_push_handoff flag makes handoff an easy-to-forget opt-in
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `enable_pre_push_handoff: bool = False` is exposed on `rebase_and_push`, while the plan only calls for threading `tmpdir` into conflict resolution. Future pre-push callers can silently degrade to generic `Stalled` by forgetting the opt-in flag, creating a maintenance trap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
