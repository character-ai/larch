### FINDING_1: [OUT_OF_SCOPE] Plan voter coverage library looks reusable by code dispatcher despite incompatible KV order
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-shell-trap-semantics-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-voter-coverage.sh` appears generic enough to be reused by code-review dispatch, but its status block order is plan-review-specific and incompatible with `dispatch-code-voters.sh`; future consolidation could break stdout parsing or path tallying.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-shell-trap-semantics-output.txt: Address the concern above.

### FINDING_2: Duplicate effective-judge counting loops can diverge
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `voter_coverage_compute_effective_judges` duplicates identical logic for argv and stdin branches, creating a future maintenance risk if only one branch is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_6: [OUT_OF_SCOPE] Dispatch voter waterfall fixture complexity is increasing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The waterfall test stub has grown more complex with status matrices and argv logging, making future dispatcher test changes more fixture-heavy.
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

### FINDING_9: Degraded warning tests key off failed status instead of effective judge count
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The degraded warning matrix asserts behavior based on external failed status rather than the actual effective judge count, so future failures without `status=failed` could break coverage math undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Required checks were not run in reviewer session
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The reviewer did not run `make lint`, `test-dispatch-plan-voters`, or `test-tally-plan-review`, so merge readiness depends on separate verification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] design-tmpdir remains an unconstrained write root
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `--design-tmpdir` is still caller-supplied without a realpath or prefix jail, so a compromised or misconfigured orchestrator could direct artifacts outside the intended session tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] emit_kv does not escape embedded newlines
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `emit_kv` leaves embedded newlines unescaped, so a path value containing `\n` could split the contract stream for naive line parsers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: Waterfall timeout increase can greatly extend design round wall clock
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The 1860-second per-voter waterfall cap can apply sequentially to Voters 2 and 3, increasing worst-case external wall clock far beyond the old 1200-second cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: Tally-error exits may leave stub files that downstream code still opens
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Some error exits can write `voting-tally.md` stubs while omitting `VOTING_TALLY_FILE` from stdout; downstream code may default the file path and consume an abort stub despite `tally-error` status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Docs claim tally stub is always written after tmpdir validation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `tally-plan-review.md` says `voting-tally.md` is always written before non-zero exit after tmpdir validation, but some assign-voter and argv failures exit without `write_tally_stub`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] main-agent-vote-required exactly-once assertion is pre-existing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The `main-agent-vote-required` test lacks the same exactly-once emission assertion as the ok path, but the reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: EXIT trap can lose original exit code under errexit
- **Reviewer(s)**: dyn-shell-trap-semantics-output.txt
- **Severity**: important
- **Concern**: `cleanup` runs under `set -euo pipefail`; if a trap command fails after recording `$?`, Bash 3.2 can replace the script’s intended exit status with the trap failure status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-trap-semantics-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] return from EXIT trap is not the fragile part
- **Reviewer(s)**: dyn-shell-trap-semantics-output.txt
- **Severity**: nit
- **Concern**: Bash 3.2 preserves an explicit outer exit status when an EXIT-trap function returns; the actual trap fragility is `errexit` inside the handler, not `return "$rc"` on success paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-trap-semantics-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Success guard can hide partial KV emission failure
- **Reviewer(s)**: dyn-shell-trap-semantics-output.txt
- **Severity**: nit
- **Concern**: `_tally_status_emitted=true` is set immediately before success `emit_kv` calls, so a later emit failure can leave callers with a partial success KV stream and no trap fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-trap-semantics-output.txt: Address the concern above.
