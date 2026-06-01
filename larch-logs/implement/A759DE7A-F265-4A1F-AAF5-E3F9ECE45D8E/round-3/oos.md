### FINDING_18: [OUT_OF_SCOPE] Python merge parity not in harness-5 CI shard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Bash `test-merge-pr` and `py-test` run in separate CI shards. Python merge bugs may not fail harness-5; only bash `merge-pr.sh` is guarded there until Phase 7 wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: At Phase 7 wire parity tests into py-test or shared gate.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_34: [OUT_OF_SCOPE] branch contains non-Phase-5 files (rebase, upgrade-larch)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Branch includes changes outside the Phase 5 plan file list; not actionable for Phase 5 fidelity review of the scoped ports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: N/A


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_35: [OUT_OF_SCOPE] acceptance lint/tests not verified in this review
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Acceptance requires `make py-lint` and `make py-test` pass; this read-only pass did not execute them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Run make py-lint and make py-test before merge


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] push.py always uses origin, not upstream
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Plan mentions origin vs upstream; `push.py` always pushes to `origin` like `git-push.sh`. Fork workflows expecting `upstream` will not get it from Python without an explicit contract or `remotes()`-based selection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document origin-only contract or implement remotes()-based selection if required.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

