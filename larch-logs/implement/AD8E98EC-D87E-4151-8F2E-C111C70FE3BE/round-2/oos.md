### OOS_1: [OUT_OF_SCOPE] Collector ignores rich `.diag` for `CURSOR_EMPTY_RESPONSE`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-diag-format-safety-output.txt
- **Severity**: latent
- **Concern**: `scripts/collect-agent-results.sh` overwrites or hardcodes generic `FAILURE_REASON` for `CURSOR_EMPTY_RESPONSE` and does not consume the new launcher `.diag`; panel summaries and execution-issues show degraded-backend text until collector work (e.g. #3392). Primary consumer of enriched diagnostics today is failure-log composition, not the collector RESULTS row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Have build_failure_reason prefer .diag for CURSOR_EMPTY_RESPONSE (likely in #3392).
  - From cursor-specialist-edge-cases-output.txt: Call build_failure_reason when .diag exists or document sidecar-only visibility until collector work lands.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] `compose-collector-failure-log.sh` cats `.diag` without secret redaction
- **Reviewer(s)**: dyn-diag-format-safety-output.txt
- **Severity**: latent
- **Concern**: Pre-existing: `.diag` sections are `cat` without `render_failed_agent_stderr_tail` / secret redaction; this branch amplifies how much untrusted content can land there, but the missing redaction path predates #3393.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] `${OUTPUT}.diag.$$` temp naming — no practical collision
- **Reviewer(s)**: dyn-diag-format-safety-output.txt
- **Severity**: nit
- **Concern**: Distinct `OUTPUT` paths per slot and per-process `$$` make `${OUTPUT}.diag.$$` temp naming a non-issue in parallel burst; cleanup removes temp files. No change required for safety on that basis alone.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

