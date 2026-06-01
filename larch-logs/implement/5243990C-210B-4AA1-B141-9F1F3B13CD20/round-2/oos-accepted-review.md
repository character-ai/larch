### FINDING_11: [OUT_OF_SCOPE] Step 18 KV parsing with `awk -F=` truncates embedded equals
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Step 18 parses wrapper KVs with `awk -F= print $2`, which would truncate future values containing `=`, though current boolean KVs are safe and one reviewer marked this pre-existing/out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_17: [OUT_OF_SCOPE] Step 18b E2 harness uses stubs instead of real renderers
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The E2 harness stubs `write-final-report` / `token-report`, so real renderer/env interactions are not cross-tested here; reviewer marked this out of scope because renderer authority remains elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_19: [OUT_OF_SCOPE] `plugin-root.env` sourcing can redirect helper execution
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Malicious tmpdir content could alter `PLUGIN_ROOT` and cause attacker-controlled helper execution, but the reviewer marked this as the pre-existing Step 18 trust model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_2: [OUT_OF_SCOPE] `STEP17_EMITTED_PRESENT` is parsed but unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Step 18b parses `STEP17_EMITTED_PRESENT`, but orchestration prose/guards do not use it; reviewers disagree whether this is in scope, but the shared risk is a dead KV being mistaken for load-bearing state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_20: [OUT_OF_SCOPE] `record-attempt` writes unsanitized argv into attempts file
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `record-attempt` prints unsanitized `--class` / `--signature` values into attempts state, allowing crafted CLI args to corrupt attempts format; reviewer marked it outside this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_21: [OUT_OF_SCOPE] Missing prebody snapshot can make `cmp` report changed body
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-teardown-boundary-output.txt, dyn-bash32-output.txt
- **Severity**: important
- **Concern**: If `.step18-prebody` is missing while `.step17-emitted` exists, `cmp` can treat an unchanged report as changed and trigger a full body re-emit; some reviewers marked this as pre-existing/out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-teardown-boundary-output.txt, dyn-bash32-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_22: [OUT_OF_SCOPE] Step 18 no longer has `--print-stdout` as a Bash-output backstop
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt, dyn-teardown-boundary-output.txt
- **Severity**: latent
- **Concern**: Removing `--print-stdout` means the collapsible Bash duplicate no longer backs up summary body visibility; reviewers describe this as an intentional/documented trade-off.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt, dyn-teardown-boundary-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_24: [OUT_OF_SCOPE] `SEEDED=false` terminal path lacks retry/abort guidance
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If seed-fresh fails when no prior state exists, the orchestrator may proceed to bug-comment behavior without durable `STALL_TRACKING`; reviewer marked this pre-existing ambiguity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_25: [OUT_OF_SCOPE] `read-session-env-key.sh` lacks explicit trailing `exit 0`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The script relies on the last emit succeeding rather than ending with an explicit `exit 0`; reviewer marked this as a clarity issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_27: [OUT_OF_SCOPE] Operational-failure KV emission is implemented and tested
- **Reviewer(s)**: dyn-bash-state-output.txt
- **Severity**: nit
- **Concern**: Reviewer reports the planned `CLEARED=false` / `SEEDED=false` emission on operational failures and related guards are implemented/tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_28: [OUT_OF_SCOPE] NEVER #20 non-write boundaries are preserved
- **Reviewer(s)**: dyn-bash-state-output.txt, dyn-teardown-boundary-output.txt
- **Severity**: nit
- **Concern**: Reviewers report the wrapper does not emit `summary-final.md` or write `.step17-emitted`, preserving prompt-side ownership of the sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt, dyn-teardown-boundary-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_30: [OUT_OF_SCOPE] `EMIT_BODY` gate is stricter than prior inline flag
- **Reviewer(s)**: dyn-teardown-boundary-output.txt
- **Severity**: nit
- **Concern**: Reviewer reports the new `EMIT_BODY` gate correctly requires `WFR_RC=0` and non-empty `summary-final.md`, hardening the old path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-boundary-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_32: [OUT_OF_SCOPE] Bash 3.2 constructs appear acceptable
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: Reviewer reports the branch does not introduce forbidden Bash 4+ constructs and uses patterns already present in the repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_33: [OUT_OF_SCOPE] Round 1 already tightened state handling and plugin-root rebinding
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes prior round changes already tightened empty/comment-only state handling and fixed `PLUGIN_ROOT` rebinding after `plugin-root.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_6: [OUT_OF_SCOPE] `stall-recovery-report.sh` is growing large
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The already-large multi-subcommand `stall-recovery-report.sh` continues to grow, increasing maintenance cost, though the reviewer marked this as not blocking the extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


