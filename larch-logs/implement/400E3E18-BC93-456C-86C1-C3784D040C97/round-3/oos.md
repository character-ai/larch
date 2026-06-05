### FINDING_13: [OUT_OF_SCOPE] design-publish mktemp failure artifact is self-deleted
- **Reviewer(s)**: dyn-artifact-publish-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The mktemp-failure path writes `timing-report-final.failure.log`, passes it to `append-tool-failure.sh`, then removes all `timing-report-final.*`. Publishing remains safe, but the create-use-delete pattern is fragile and leaves no artifact for later inspection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-publish-output.txt, cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_14: [OUT_OF_SCOPE] Design per-round counts may use cumulative tally files
- **Reviewer(s)**: dyn-artifact-publish-output.txt
- **Severity**: latent
- **Concern**: `record-plan-review-round-timing.sh` derives accepted/rejected counts from session-root tally files rather than round-local snapshots, so multi-round JSON can attribute cumulative counts to individual rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-publish-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=1 Result=neutral

### FINDING_18: [OUT_OF_SCOPE] timing-report emit_round_array relies on fragile global awk array cleanup
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-bash32-compat-output.txt, dyn-interval-attachment-output.txt
- **Severity**: latent
- **Concern**: `emit_round_array` uses global awk arrays for match/dedup state and depends on manual cleanup. Current behavior appears correct, but stale global state or future cleanup changes could corrupt per-step round attachment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-bash32-compat-output.txt, dyn-interval-attachment-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] record-plan OOS tally falls back to $NF for result
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `record-plan-review-round-timing.sh` falls back to `$NF` when the expected Result column is empty or dashed. If a generated table ever has extra trailing fields, OOS accepted/rejected counts could be wrong.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_23: [OUT_OF_SCOPE] timing-report sidecar exclusions may look dead without context
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The design-publish/render-final-summary ordering means sidecar exclusions are defense-in-depth for pre-publish render paths, not always exercised by post-publish failure flow. Future reviewers might remove them as apparently dead without this context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_24: [OUT_OF_SCOPE] record-plan helper can resolve the implement ledger if IMPLEMENT_TMPDIR leaks
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `record-plan-review-round-timing.sh` reportedly does not clear `IMPLEMENT_TMPDIR` before invoking `timing-ledger.sh`. If `LARCH_TIMING_LEDGER` is absent, ledger resolution may fall through to an implement ledger path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_27: [OUT_OF_SCOPE] Design snapshot timing silently no-ops when round_start is empty
- **Reviewer(s)**: dyn-interval-attachment-output.txt
- **Severity**: latent
- **Concern**: `_emit_plan_round_timing_row` silently returns when `_round_start` is empty. The reviewer characterized this as a pre-existing structural risk inherited by new emission points.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-interval-attachment-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_28: [OUT_OF_SCOPE] design publish render failure can log exit code 0 for invalid JSON
- **Reviewer(s)**: dyn-handoff-telemetry-output.txt
- **Severity**: latent
- **Concern**: If timing render succeeds but JSON validation fails, the failure path may log an effective exit code of `0` to `execution-issues.md`, making a render failure appear successful.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-handoff-telemetry-output.txt: Address the concern above.

Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] run-log docs omit the new per-step rounds array
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `docs/run-logs.md` documents `timing-report.json` but does not describe the optional per-step `rounds` sub-array, so operators may not know committed timing JSON includes round-level detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

