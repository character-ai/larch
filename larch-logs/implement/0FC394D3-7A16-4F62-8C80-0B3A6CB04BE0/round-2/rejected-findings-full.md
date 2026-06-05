### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: LARCH bump-file parsing uses os.pathsep instead of documented colon separator
- **Reviewer(s)**: dyn-bump-classifier-output.txt
- **Severity**: latent
- **Concern**: `_larch_bump_files()` splits `LARCH_VERSION_FILES` / `LARCH_BUMP_FILES` on `os.pathsep`. This matches bash on Unix but would accept semicolon-delimited lists on Windows, diverging from the documented colon-only bash contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bump-classifier-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Public enable_pre_push_handoff flag makes handoff an easy-to-forget opt-in
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `enable_pre_push_handoff: bool = False` is exposed on `rebase_and_push`, while the plan only calls for threading `tmpdir` into conflict resolution. Future pre-push callers can silently degrade to generic `Stalled` by forgetting the opt-in flag, creating a maintenance trap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: No in-scope bash parity harness covers non-bump conflict classification
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Python’s non-bump conflict classification can drift from bash `ship_pr_vendor_conflict_csv_is_non_bump_only` without CI detection, as shown by the CHANGELOG mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Ship driver loses pre-push handoff metadata at the goto_rebase boundary
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `PrePushConflictHandoff` is a `Stalled` subclass, so `_error_to_result` collapses it to generic `Outcome.STALLED`. The goto-rebase path writes the flag but does not preserve `conflict_files`, `resume_phase`, `caller_kind`, or equivalent state/JSON metadata needed by orchestration to dispatch conflict resolution. This creates a flag-only partial handoff that is not recoverable from driver outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Handoff flag write trusts IMPLEMENT_TMPDIR without allowed-root validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_write_handoff_flag` can fall back to `IMPLEMENT_TMPDIR` without applying `ship.py`’s allowed-root validation. A library caller or harness with `enable_pre_push_handoff=True` and no explicit `tmpdir` could be steered into writing the handoff flag outside the intended session tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

