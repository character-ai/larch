### FINDING_19: [OUT_OF_SCOPE] Vendor rotation test brittleness (launcher-order line)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Vendor rotation assertion uses the third line of launcher-order rather than direct tier-0 on `_fix_attempt=1`. The test could pass or fail for retry side effects rather than rotation semantics; pre-existing brittleness not introduced solely by behind-count wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Prefer asserting first launcher on second outer attempt equals codex when _fix_attempt=1.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_20: [OUT_OF_SCOPE] CI_FIX_REBASE_PENDING push-only retry may skip job re-verify (pre-existing)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Pre-existing retry shape: push-only `CI_FIX_REBASE_PENDING` retry with empty `failed_jobs_tsv` when `gh-run-logs` is unavailable may skip failed-job re-verification before force-push after rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Consider threading last-known TSV on pending retry.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_5: [OUT_OF_SCOPE] Duplicate BEHIND_COUNT KV parsing (awk vs kv_value)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `ci-status.sh` and `ship-pr.sh` duplicate parsing of the `BEHIND_COUNT` contract (inline awk vs `kv_value`). Future helper output changes require two edits with drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared parse helper for both scripts.
  - From cursor-specialist-plan-fidelity-output.txt: Optionally route through kv_value for consistency with ship-pr.sh.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


