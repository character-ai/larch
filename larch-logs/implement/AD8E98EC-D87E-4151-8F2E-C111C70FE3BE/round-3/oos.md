### OOS_1: [OUT_OF_SCOPE] Exit-code transient branch lacks stdout quota grep present on empty-result path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Exit-code transient guard does not grep `$OUTPUT` for quota; empty-result guard does. Quota-only-on-stdout with exit 8 may burn exit-code retries (pre-existing asymmetry).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add external_is_quota_failure on $OUTPUT to the exit-code transient branch.

---


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Collector overwrites rich `.diag` for `CURSOR_EMPTY_RESPONSE`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/collect-agent-results.sh` overwrites rich `.diag` with generic `FAILURE_REASON` for `CURSOR_EMPTY_RESPONSE` (pre-existing); operators may not see new envelope diagnostics in pipe-delimited `RESULTS` even when `.diag` is populated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Align collector with .diag KV grammar when #3392 lands (not introduced by this diff).

---


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] No panel-level cursor launch concurrency cap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Parallel dispatch can still launch eight cursor slots with no global in-flight limit; jitter/retry logic is per-process only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Consider a future global cursor concurrency cap in the dispatcher (separate change).

---


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Doc “six total” worst-case call count slightly overstated
- **Reviewer(s)**: dyn-retry-budget-integrity-output.txt
- **Severity**: latent
- **Concern**: `scripts/launch-review.md` and related docs claim worst case “six total” backend calls (3 exit-code + 3 empty-result); in one auth-loop pass the achievable maximum is five (two exit-code retries then three empty-result attempts) because a third consecutive exit-8 breaks out without entering the empty-result branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retry-budget-integrity-output.txt: (Concern documents arithmetic only; no explicit fix bullet in source.)

---


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] chore(larch-logs) flush
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Commit `cd318f2d7` — chore(larch-logs) flush is out of scope per review instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No fix direction in source beyond out-of-scope note.)

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

