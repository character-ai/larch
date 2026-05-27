# Review Round 1

- Mode: `diff`
- 7 accepted, 4 rejected (3 exonerated)

## Accepted Findings

### FINDING_14: Tally-error exits may leave stub files that downstream code still opens
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Some error exits can write `voting-tally.md` stubs while omitting `VOTING_TALLY_FILE` from stdout; downstream code may default the file path and consume an abort stub despite `tally-error` status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: EXIT trap can lose original exit code under errexit
- **Reviewer(s)**: dyn-shell-trap-semantics-output.txt
- **Severity**: important
- **Concern**: `cleanup` runs under `set -euo pipefail`; if a trap command fails after recording `$?`, Bash 3.2 can replace the script’s intended exit status with the trap failure status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-trap-semantics-output.txt: Address the concern above.


### FINDING_3: Coverage library docs claim severity preservation outside its responsibility
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-voter-coverage.md` documents severity preservation even though the library does not handle severity, which can mislead future maintainers about module responsibilities.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: Tally-error regression coverage misses several exit-2 paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-trap-semantics-output.txt
- **Severity**: latent
- **Concern**: The tally harness only asserts exactly-once `tally-error` behavior for one missing-argument path, leaving ballot-unreadable, malformed ballot, missing voter, mutual-exclusion, and other validation exits insufficiently covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-trap-semantics-output.txt: Address the concern above.


### FINDING_5: Dispatch voter key-order test may fail on valid WARN placement
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The healthy-path byte-order assertion assumes no optional `WARN` keys before the voter status block, so valid warning output could fail the test despite preserving the contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_7: Tally review docs overstate status emission for --help
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-trap-semantics-output.txt
- **Severity**: latent
- **Concern**: `tally-plan-review.md` says `TALLY_PLAN_REVIEW_STATUS` is emitted on every exit path, but `-h|--help` exits 0 after usage output without emitting any status KV.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-trap-semantics-output.txt: Address the concern above.


### FINDING_8: Main-agent-vote-required path lacks exactly-once status assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The zero-voter `main-agent-vote-required` success path does not assert exactly-once status emission, so a double-emission regression on that branch would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


