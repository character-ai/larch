### FINDING_11: [OUT_OF_SCOPE] Pre-existing version race machinery now affects ship indirectly
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The version race gate pre-exists, but the Python ship path now depends on merge machinery that still contains it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_12: [OUT_OF_SCOPE] Bash Step 8+ docs still describe unconditional ship state writes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/SKILL.md` still documents bash-style `ship-pr-state.sh` writes for all Step 8+ runs, although Python may not use that file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_17: [OUT_OF_SCOPE] Legacy exit alias ambiguity predates this change
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-ship-state-output.txt, dyn-bash-parity-output.txt, dyn-finalize-flow-output.txt
- **Severity**: latent
- **Concern**: Multiple reviewers flagged the pre-existing `EXIT_BAIL` / `EXIT_STALL` alias collision as future misrouting risk, though not introduced by the new driver path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-ship-state-output.txt, dyn-bash-parity-output.txt, dyn-finalize-flow-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_21: [OUT_OF_SCOPE] PR titles are not redacted before `gh pr create`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Commit-derived PR titles may expose accidental tokens publicly; reviewer notes this matches existing bash behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_38: [OUT_OF_SCOPE] `flush_logs_post` ordering test is absent
- **Reviewer(s)**: dyn-runlogs-output.txt
- **Severity**: latent
- **Concern**: Reviewer separately flagged the missing test asserting manifest `status=done` is written before `_write_final_report`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlogs-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_39: [OUT_OF_SCOPE] Pre-push log commit failures are allowed by policy
- **Reviewer(s)**: dyn-runlogs-output.txt
- **Severity**: latent
- **Concern**: `REFRESH_SKIP_MERGE_OK` includes `commit-failed`, so ship can continue without committed run logs; reviewer notes this mirrors bash but remains a policy risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlogs-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_42: [OUT_OF_SCOPE] Python teardown omits bash Step 18 safety nets
- **Reviewer(s)**: dyn-finalize-flow-output.txt
- **Severity**: latent
- **Concern**: Python teardown lacks several bash Step 18 behaviors, including process cleanup, execution-issues safety net, manifest recovery/commit, and tmpdir cleanup helper usage. Reviewer notes live Step 18 still calls bash today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-flow-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_45: [OUT_OF_SCOPE] Driver CI-loop coverage remains absent
- **Reviewer(s)**: dyn-ci-handback-output.txt
- **Severity**: latent
- **Concern**: Reviewer separately notes driver-level tests do not cover CI monitor loop threading, caps, transient exit 6, or CI-fix handback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-handback-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_47: [OUT_OF_SCOPE] Harness shard wiring is considered sufficient
- **Reviewer(s)**: dyn-harness-gate-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes `test-merge-parity` and pytest pinning are wired as intended, so no `ci.yaml` edit is required for that part.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-gate-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_48: [OUT_OF_SCOPE] Finalize parity is split between smoke and full harness
- **Reviewer(s)**: dyn-harness-gate-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes lightweight Python finalize parity and full bash harness coverage are split; operators should not treat the Python file alone as full parity coverage until skip behavior is fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-gate-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


