### FINDING_11: [OUT_OF_SCOPE] relevant-checks does not map tmpdir validator changes to its harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/relevant-checks.sh` has no direct mapping from `lib-design-tmpdir` changes to `make test-lib-design-tmpdir`, so developers relying on relevant checks may miss the focused harness until broader linting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_12: [OUT_OF_SCOPE] tmpdir validate-to-mkdir TOCTOU remains
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Callers validate one path but later `mkdir` the original argv, leaving a symlink-swap window where a validated shared tmpdir can be replaced before artifact creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_13: [OUT_OF_SCOPE] emit_kv allows newline keys
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `emit_kv` does not reject newlines in keys, which could split FD 3 parsers if keys ever become dynamic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_16: [OUT_OF_SCOPE] branch includes unrelated work
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The branch includes substantial unrelated `#3122` work alongside the OOS hardening, so reviewers evaluating this PR against the plan should isolate the relevant commits from the broader branch delta.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_4: [OUT_OF_SCOPE] changelog references removed voter coverage filename
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Historical `CHANGELOG.md` entries still reference `scripts/lib-voter-coverage.sh`; this is outside the acceptance grep scope but may confuse readers looking for the removed filename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_7: [OUT_OF_SCOPE] remaining design tmpdir consumers are unwired
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Multiple other `--design-tmpdir` consumers still do not call `larch_design_tmpdir_validate`, so misconfigured orchestrators or publish/preview paths can still write outside the allowlist pending the deferred broader sweep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


