### FINDING_1: [OUT_OF_SCOPE] Unused `pr_view_current` helpers add dead surface or should be wired into PR recovery
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-contracts-output.txt, dyn-python311-compat-output.txt
- **Severity**: important
- **Concern**: `pr_view_current` / `pr_view_current_read` are newly present but unused. Reviewers disagree whether to remove them or wire them into post-create PR recovery, but the shared risk is dead API surface and unclear intended recovery behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-contracts-output.txt, dyn-python311-compat-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_14: [OUT_OF_SCOPE] `--no-logs-commit` parity can diverge across Python ship paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `--no-logs-commit` is not consistently forwarded/read across Python invoke and pre-rebase flush paths, so state-file side effects and `ctx.no_logs_commit` can diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_18: [OUT_OF_SCOPE] `gh pr create` no-`--json` coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-gh-cli-contracts-output.txt
- **Severity**: nit
- **Concern**: Only some `pr_create` paths assert absence of `--json`, and recorded fixtures do not catch host-specific output drift beyond the fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-gh-cli-contracts-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_24: [OUT_OF_SCOPE] `emit_result` lacks explicit flush
- **Reviewer(s)**: dyn-stdout-protocol-output.txt
- **Severity**: nit
- **Concern**: `emit_result` does not use `flush=True`; safe today because the process exits immediately, but potentially brittle for future streaming readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdout-protocol-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_25: [OUT_OF_SCOPE] Step 8+ prose still references state-file routing on Python path
- **Reviewer(s)**: dyn-stdout-protocol-output.txt
- **Severity**: latent
- **Concern**: Step 8+ documentation still routes several branches through `ship-pr-state.sh` even though the Python selector says not to use that file for Python-path routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdout-protocol-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_26: [OUT_OF_SCOPE] Normal stdout protocol path was verified OK
- **Reviewer(s)**: dyn-stdout-protocol-output.txt
- **Severity**: nit
- **Concern**: Under default invocation without lib-quiet stdout redirect, stdout carries exactly one JSON object and subprocess output does not leak into driver stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdout-protocol-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_27: [OUT_OF_SCOPE] Local Python floor helper test provides little regression value
- **Reviewer(s)**: dyn-python311-compat-output.txt
- **Severity**: nit
- **Concern**: `test_python_ship_driver_version_guard_probe` tests a local helper rather than the runtime probe expression, so it cannot catch drift in the actual guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python311-compat-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


