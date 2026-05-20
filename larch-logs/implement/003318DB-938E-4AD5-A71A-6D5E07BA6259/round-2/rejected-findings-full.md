### [rejected] FINDING_10

### FINDING_10: code-quality: scripts/dispatch-code-voters.sh:240-246
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unconditional rm -f of the first-pass sidecar path runs before parse-rate classification, including on OK/SKIPPED early return; not described in the feature plan or dispatch-code-voters.md. Extra no-retry filesystem side effect and potential confusion when operators expect only retry-success paths to touch sidecars. Document the cleanup contract in dispatch-code-voters.md or move rm to immediately before cp on the retry-success branch if stale cleanup is not required on OK paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

### FINDING_11: code-quality: scripts/dispatch-code-voters.sh:240-252
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate case "$voter_path" blocks compute sidecar and retry temp paths separately. Future edits could update one case and forget the other, reintroducing inconsistent suffix handling. Consolidate into one case arm that assigns both locals.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

### FINDING_13: correctness: scripts/dispatch-code-voters.sh:240-246;scripts/test-dispatch-code-voters.sh (retry_fail_claude/codex blocks)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Entry rm -f of the sidecar plus tests that seed then assert ! -e conflate cleanup with no-copy-on-failure. A future change could remove entry rm while wrongly adding a cp on the fail branch; tests might still pass or fail for the wrong reason relative to plan intent. Remove unconditional sidecar rm or adjust tests to prove no copy on failure without relying on prior deletion.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

### FINDING_15: risk-integration: scripts/dispatch-code-voters.sh:240-246
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Unconditional rm -f of first_pass_sidecar before parse-rate outcome is known A pre-existing *-vote-output-first-pass.txt beside the canonical voter file is deleted when check_and_retry_voter_parse_rate runs even if status is OK and no retry occurs (e.g. reused REVIEW_TMPDIR or tooling-seeded sidecar). Move rm to the retry-success path before cp and/or only after NOT_SUBSTANTIVE; adjust harness to assert no sidecar without depending on entry-time deletion.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

### FINDING_17: risk-integration: scripts/dispatch-code-voters.sh:263-265
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] emit_breadcrumb is forced through >&2 to avoid polluting command-substitution stdout for parse-rate status. Quiet-log FD layout or capture idioms could change, risking breadcrumb text leaking into VOTER_*_PARSE_RATE_STATUS or mis-routing diagnostics. Re-validate whenever lib-quiet init or the $(check_and_retry_voter_parse_rate ...) call pattern changes; consider a dedicated helper that logs without touching FD1 of the capture subshell.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

### FINDING_8: architecture: scripts/dispatch-code-voters.sh:240-244
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Unplanned rm -f of first_pass_sidecar before status check. Deletes any existing first-pass sidecar even when returning immediately with OK parse rate. Document as intentional hygiene or restrict rm to the retry-success branch per plan scope.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

### FINDING_9: code-quality: scripts/dispatch-code-voters.md:126-127 vs scripts/dispatch-code-voters.sh:189-192
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc implies generic best-effort copy/breadcrumb; code emits breadcrumb only after successful cp. Operators may expect a breadcrumb whenever retry promotion succeeds even if copy failed; minor mismatch only. Note in doc that breadcrumb is tied to successful sidecar write, or emit a different stderr line when cp fails but promotion proceeds.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

