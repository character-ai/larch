### [rejected] FINDING_11

### FINDING_11: correctness: scripts/dispatch-code-voters.sh:240-246
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Unconditional rm -f of the first-pass sidecar runs before the NOT_SUBSTANTIVE branch, so the no-retry path deletes any pre-existing *-vote-output-first-pass.txt beside the voter file. A reused or manually populated review tmpdir still holds a first-pass sidecar from an earlier parse-retry; a later run where that voter parses cleanly on first pass deletes the sidecar without performing any retry, silently dropping the earlier preserved narrative. Restrict rm to the parse-retry success branch (or to the NOT_SUBSTANTIVE path only), immediately before cp, so the happy path does not unlink unrelated prior sidecars.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

### FINDING_13: risk-integration: scripts/dispatch-code-voters.sh:240-245
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Unconditional rm -f of first_pass_sidecar before parse classification A pre-existing *-vote-output-first-pass.txt in REVIEW_TMPDIR can be deleted when the voter ends OK without retry Restrict rm to the NOT_SUBSTANTIVE retry path or document filename ownership and deletion semantics
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

### FINDING_14: risk-integration: scripts/dispatch-code-voters.sh:240-246
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Unconditional rm -f of the first-pass sidecar before parse-rate classification deletes a prior run sidecar even when the current run exits early on substantive OK without a retry. Second dispatch-code-voters invocation (or any reuse of the same REVIEW_TMPDIR paths) after an earlier parse-retry success can remove *-vote-output-first-pass.txt before returning OK, losing first-pass observability with no replacement copy. Restrict rm to the NOT_SUBSTANTIVE path or to immediately before the successful-branch cp (avoid unlink on substantive OK early return).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

### FINDING_15: risk-integration: scripts/dispatch-code-voters.sh:244-172
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] rm -f runs before early return on non-NOT_SUBSTANTIVE status, deleting any existing sidecar beside voter_path even when no retry runs. Reuse of a tmpdir with a leftover first-pass artifact while parse-rate is OK: artifact is deleted without retry. Move rm -f to the retry-success branch only or gate on harness/production context if deletion is only for test hygiene.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

### FINDING_16: risk-integration: scripts/dispatch-code-voters.sh:244-246
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unconditional rm -f of first-pass sidecar before parse-rate classification OK fast-path deletes any pre-existing sidecar at that path in REVIEW_TMPDIR without a retry Restrict rm to retry-success path or NOT_SUBSTANTIVE branch if foreign sidecars must survive no-retry runs
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

### FINDING_17: risk-integration: scripts/dispatch-code-voters.sh:263-267
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan showed unconditional cp || true plus one breadcrumb; code uses conditional cp emit_breadcrumb to stderr and larch_err on cp failure. No functional mismatch with stated fail-open promotion; minor plan drift. Accept as-is or align comments/plan text with the richer behavior.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

### FINDING_18: risk-integration: scripts/dispatch-code-voters.sh:263-268
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Conditional cp + larch_err instead of plan silent cp || true and always-on breadcrumb Monitoring or docs tied to the plan may expect a breadcrumb whenever retry succeeds even if cp fails Align code with plan or update plan/docs for conditional breadcrumb and larch_err on cp failure
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

### FINDING_19: risk-integration: scripts/dispatch-code-voters.sh:263-268
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Implementation uses conditional cp + larch_err instead of plan's silent cp || true and always-on breadcrumb Operators or docs aligned to the plan may expect a breadcrumb whenever retry succeeds even if cp fails; plan-code drift Align implementation with plan or update plan/docs to describe conditional breadcrumb and larch_err on cp failure
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

### FINDING_2: architecture: scripts/dispatch-code-voters.sh:236-244
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Unplanned upfront rm -f of the first-pass sidecar before parse-rate classification. Not in the implementation plan; behavior is understandable for harness stale files but is not requirement-traceable. Document as intentional or restrict/move rm so it is plan-aligned.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

### FINDING_20: risk-integration: scripts/test-dispatch-code-voters.sh (retry harness)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No automated coverage for cp failure while mv still promotes A refactor could tie mv to cp success and regress fail-open behavior Add a focused test if an established cp-failure simulation pattern exists
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

### FINDING_21: risk-integration: scripts/test-dispatch-code-voters.sh:424-483 scripts/test-dispatch-code-voters.sh:546-568
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Retry-fail tests seed stale first-pass file then assert absence; coupled to entry rm and no cp on fail Maintainers may read the test as proving cp never runs on failure without noticing seed+rm interaction Add a harness comment or use a fresh tmpdir without seeding for a stricter contract
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

### FINDING_6: code-quality: scripts/dispatch-code-voters.sh:240-252
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate case on voter_path for first_pass_sidecar and retry_output. Future naming changes might update one case and miss the other. Single case arm assigning both derived paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

