### FINDING_10: [OUT_OF_SCOPE] Direct Codex call sites bypass stdin guard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Some scripts invoke `codex exec` directly rather than through `run-external-agent.sh`, so they do not inherit the new `< /dev/null` spawn-layer guard if later backgrounded without prompt-file redirection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] Initial launches inherit gated test-hook environment
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Initial voter/reviewer launches via `dispatch-with-waterfall.sh` may inherit `LARCH_ALLOW_TEST_HOOKS` and `LARCH_TEST_TRAP_*` from the parent environment, unlike retry relaunches that strip them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] Negotiation events JSONL may persist sensitive content
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Negotiation Codex `--json` streams can contain prompts and tool output on disk beside response files until session tmpdir cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_18: [OUT_OF_SCOPE] Test harness uses awk plus eval
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-larch-log.sh` extracts a function body with `awk` and `eval`; it is test-only but still avoidable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] breadcrumb-monitor early exit remains unresolved
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `breadcrumb-monitor.sh` can still let the orchestrator misread Step 5 status while `review-and-fix` continues in the background.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] run-external-agent stderr progress contract is undocumented
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Progress diagnostics moved to stderr without a matching `run-external-agent.md` contract update, so future callers may mis-handle stdout/stderr expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] Branch mixes unrelated concerns
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch appears to mix the #2973 voter fix with unrelated telemetry, parser, validation, and log changes, making review, bisect, and revert harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] skipped voter status is documented but not produced
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `VOTER_2_STATUS=skipped` is documented or handled, but the waterfall path does not produce it, leaving dead or untested conditional behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] Parse-rate retries backfill .done outside the new barrier
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Parse-rate retry relaunches still backfill `${retry_output}.done` immediately after synchronous relaunch instead of using the new voter wait-barrier pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

