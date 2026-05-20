### [rejected] FINDING_11

### FINDING_11: correctness: scripts/collect-agent-results.sh:1292-1298
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Structured NS success publishes the sidecar with cp instead of the plan’s mv, leaving duplicate structured files at the ns-retry path and the final path. Two copies of the same sidecar after success; confusing if something later edits the retry-path copy. Use mv if single-copy semantics are required.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

### FINDING_12: correctness: scripts/collect-agent-results.sh:1292-1298
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Structured NS-retry success publishes the structured sidecar with cp instead of the planned mv. After success, STRUCTURED_SIDECAR may point at ORIG_OUTPUT.* while an identical file remains on the NS-retry path; plan assumed relocation off the retry path. Use mv as in the plan, or amend the plan/spec to require duplicate sidecars on disk.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

### FINDING_13: correctness: scripts/collect-agent-results.sh:135-168
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Retry prose is published via temp cp+mv onto ORIG_OUTPUT; NS_RETRY_OUTPUT is not mv-renamed onto ORIG_OUTPUT as the plan stated. Plan text implied mv of the retry file onto the original basename (no separate -ns-retry.txt path after success); implementation keeps a full duplicate transcript at -ns-retry.txt. Decide whether retaining -ns-retry.txt is normative; if not, switch to the plan’s mv (after first-pass copy) or update the plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

### FINDING_14: correctness: scripts/collect-agent-results.sh:144-150
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] First-pass cp failure fails closed; plan snippet only showed the success breadcrumb path. Stricter than the minimal plan snippet; could surprise if someone expected overwrite to proceed without a sidecar. Already documented in collect-agent-results.md in this branch; optional plan sync only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

### FINDING_15: correctness: scripts/test-collect-agent-results.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Planned C_NS_FP_FAILURE (no sentinel) is not implemented as a single named case. Reviewers tracing the plan line-by-line may look for a missing-sentinel test and not find it under that name. Add a sentinel-missing case or rename test comments to match the plan vocabulary.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

### FINDING_16: risk-integration: scripts/collect-agent-results.sh structured NS-retry; scripts/collect-agent-results.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Documented best-effort structured sidecar publish failure has no regression test. A regression in the cp-to-final branch could break consumers expecting STRUCTURED_SIDECAR beside REVIEWER_FILE without failing the harness. Add a harness that forces final sidecar cp to fail and assert STRUCTURED_SIDECAR remains on the ns-retry path plus stderr contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

### FINDING_17: risk-integration: scripts/collect-agent-results.sh:1289-1299
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Structured sidecar publish failure yields OK row with prose at ORIG_OUTPUT but STRUCTURED_SIDECAR on ns-retry path. A consumer ignores STRUCTURED_SIDECAR and reads REVIEWER_FILE.tsv/jsonl; that sibling may be absent or stale vs retry prose, producing plausible but mismatched structured+prose state. Document mandatory STRUCTURED_SIDECAR parsing for NS-retry success; or fail closed / clean up sibling sidecar if co-location is required.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

### FINDING_19: risk-integration: scripts/test-collect-agent-results.sh (NS-retry failure coverage)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan-style NS failure (missing or bad retry sentinel or empty retry output) is not explicitly asserted. Coverage relies on helper exit failure and no-meta cases; a future change could mishandle missing or invalid sentinel or empty retry transcript and still pass CI. Add a fixture omitting or corrupting *-ns-retry.txt.done (or empty retry body) and assert no *-first-pass.txt and expected STATUS.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

### FINDING_20: risk-integration: scripts/test-collect-agent-results.sh:511-520
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] C_NS_FP_PUBLISH_FAIL sources collect-agent-results.sh --source-only then calls preserve_and_publish_ns_retry relying on helpers and lib-quiet being defined before the early return gate. A refactor that moves sourcing below the gate breaks the test with command not found style failures far from the production bug. Add a comment documenting the invariant or assert the function exists after source.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

### FINDING_6: code-quality: scripts/collect-agent-results.md:24-25
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] The NOT_SUBSTANTIVE NS-retry outcome paragraph is a single dense block of many conditional clauses. Editors miss edge cases (e.g. publish vs sidecar failure) when updating one clause and accidentally contradict another. Split into short bullets mirroring nearby sections (preserve first pass publish prose structured sidecar failure modes).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

### FINDING_8: code-quality: scripts/collect-agent-results.sh:1292-1298
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Structured NS success publishes the sidecar with cp instead of the plan s mv leaving a duplicate normalized sidecar at the retry path. Operators or scripts may treat both paths as live artifacts or waste disk on large JSONL TSV bodies. Prefer mv for same directory publish or document that the retry path copy is intentionally retained garbage.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

