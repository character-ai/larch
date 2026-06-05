### FINDING_12: [OUT_OF_SCOPE] Branch includes unrelated design/timing/doc changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The diff includes unrelated design, timing, docs, or harness changes beyond finalize parity scope, making the PR harder to audit and increasing regression risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_13: [OUT_OF_SCOPE] CI-fix pending documentation/comments are stale or missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ci-rebase-output.txt
- **Severity**: latent
- **Concern**: Comments, docstrings, or README notes still describe old `CI_FIX_REBASE_PENDING` behavior or omit the new lifecycle, which can mislead maintainers and operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ci-rebase-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_16: [OUT_OF_SCOPE] Ship state writer lacks newline rejection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `_write_ship_state` writes context-sourced fields without the newline guard used by finalize state writing, so untrusted GitHub metadata could corrupt one-line-per-KV state files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_17: [OUT_OF_SCOPE] Local cleanup can destructively hard-reset default branch
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_local_cleanup` can run `git reset --hard origin/main` when flush-only heuristics match, reflecting pre-existing bash behavior but posing operational risk for Python cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated


### FINDING_18: [OUT_OF_SCOPE] Bash branch deletion is less strict than Python
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/local-cleanup.sh` deletes branches without `check-ref-format` or `--`; this is pre-existing and not a regression from the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


### FINDING_24: [OUT_OF_SCOPE] Timing report silently collapses duplicate round rows
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: nit
- **Concern**: `emit_round_array` keeps the last duplicate `(skill, step, round)` row without warning, which can hide warn-only double-writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated


### FINDING_25: [OUT_OF_SCOPE] Timing report awk globals are undeclared
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: nit
- **Concern**: `match_idx` and `round_match_pos` are undeclared awk globals, making `scripts/timing-report.sh` fragile if the function grows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


### FINDING_29: [OUT_OF_SCOPE] Remote branch state lacks transient retry
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `_remote_branch_state()` calls `git ls-remote` without the transient retry behavior bash uses, so flaky network failures may diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated


