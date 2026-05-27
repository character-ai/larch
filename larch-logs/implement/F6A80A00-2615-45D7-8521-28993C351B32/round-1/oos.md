### FINDING_1: [OUT_OF_SCOPE] Plan voter coverage library looks reusable by code dispatcher despite incompatible KV order
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-shell-trap-semantics-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-voter-coverage.sh` appears generic enough to be reused by code-review dispatch, but its status block order is plan-review-specific and incompatible with `dispatch-code-voters.sh`; future consolidation could break stdout parsing or path tallying.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-shell-trap-semantics-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_11: [OUT_OF_SCOPE] design-tmpdir remains an unconstrained write root
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `--design-tmpdir` is still caller-supplied without a realpath or prefix jail, so a compromised or misconfigured orchestrator could direct artifacts outside the intended session tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_12: [OUT_OF_SCOPE] emit_kv does not escape embedded newlines
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `emit_kv` leaves embedded newlines unescaped, so a path value containing `\n` could split the contract stream for naive line parsers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] Docs claim tally stub is always written after tmpdir validation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `tally-plan-review.md` says `voting-tally.md` is always written before non-zero exit after tmpdir validation, but some assign-voter and argv failures exit without `write_tally_stub`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] main-agent-vote-required exactly-once assertion is pre-existing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The `main-agent-vote-required` test lacks the same exactly-once emission assertion as the ok path, but the reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_18: [OUT_OF_SCOPE] return from EXIT trap is not the fragile part
- **Reviewer(s)**: dyn-shell-trap-semantics-output.txt
- **Severity**: nit
- **Concern**: Bash 3.2 preserves an explicit outer exit status when an EXIT-trap function returns; the actual trap fragility is `errexit` inside the handler, not `return "$rc"` on success paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-trap-semantics-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_19: [OUT_OF_SCOPE] Success guard can hide partial KV emission failure
- **Reviewer(s)**: dyn-shell-trap-semantics-output.txt
- **Severity**: nit
- **Concern**: `_tally_status_emitted=true` is set immediately before success `emit_kv` calls, so a later emit failure can leave callers with a partial success KV stream and no trap fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-trap-semantics-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] Dispatch voter waterfall fixture complexity is increasing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The waterfall test stub has grown more complex with status matrices and argv logging, making future dispatcher test changes more fixture-heavy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

