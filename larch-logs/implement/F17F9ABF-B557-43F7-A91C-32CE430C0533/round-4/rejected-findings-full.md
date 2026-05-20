### [rejected] FINDING_10

### FINDING_10: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:951-1612
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test matrix grows well beyond the eight regression tests requested in the feature description. Higher long-term maintenance cost and weaker traceability to the original acceptance criterion. Consolidate to eight scenarios or mark extras explicitly as optional coverage.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_12

### FINDING_12: correctness: skills/review-and-fix/scripts/review-and-fix.sh:87-105
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] important_findings_present hard-fails when any scan path is missing/unreadable Missing round-K/findings.md during convergence aborts the entire review-and-fix round with exit 2 instead of skipping or soft-handling the heuristic. Treat missing file as empty for the Important scan or document fail-closed behavior and emit a targeted breadcrumb instead of exit 2.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_13

### FINDING_13: correctness: skills/review-and-fix/scripts/review-and-fix.sh:87-106 skills/review-and-fix/scripts/review-and-fix.sh:1194-1206
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Important scan fails the entire round when any scanned findings.md is missing or unreadable. Partial tmpdir with review-core.env but no findings.md makes important_findings_present return 2 and the script exits 2 during convergence. Treat missing findings as empty for the Important scan or document fail-closed semantics in review-and-fix.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_17

### FINDING_17: correctness: skills/review-and-fix/scripts/review-and-fix.sh:PartC churn warning
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Churn warning compares to previous non-degraded round not strict round N-1 If round N-1 is degraded, warning may omit a case strict N vs N-1 semantics would flag. Use round-(N-1)/review-core.env for churn only if product requires numeric neighbors.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_20

### FINDING_20: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1211-1223
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Churn warning not gated on degraded_this_round Degraded best-effort rounds can still emit the churn warning from unstable accept counts. Extend the Part C condition with degraded_this_round==false or document the exception.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_21

### FINDING_21: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1211-1224
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Churn warning uses find_previous_non_degraded_round instead of strict round N-1 accepts. Warning may cite round Y != N-1 when round N-1 was degraded confusing operators comparing adjacent rounds. Align with strict N-1 read or document skip-degraded semantics in review-and-fix.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_22

### FINDING_22: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:139-143,1176-1206
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Convergence allowlist includes in-scope-filtered-out alongside complete/fix-applied/no-changes. Two consecutive filtered-out rounds with low accepts could emit converged-small-changes despite no applied fixes, surprising orchestrators. Exclude in-scope-filtered-out from convergence_candidate_status or document the behavior in review-and-fix.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_5

### FINDING_5: architecture: skills/review-and-fix/scripts/test-review-and-fix.sh:convergence/degraded test block
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan named TEST_CORE_STATUS degraded-panel stubs; tests use standalone REVIEW_CORE_SH stub scripts instead Named plan hook absent; harder to trace plan to code for future maintainers. Align stub mechanism with plan or update plan to match chosen pattern.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_6

### FINDING_6: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1197-1206
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Inverted if/else around important_findings_present is hard to reason about and easy to break in future edits. Future one-line edit could swap branches and silently invert Important gating. Rewrite with explicit important_rc case statement.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_7

### FINDING_7: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1211-1224
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Churn warning compares against the previous non-degraded round, not strictly round N-1 as the plan text states. When round N-1 is degraded, the warning references an older round, which can diverge from the stated “N vs N-1” semantics. Update docs/plan wording or add an explicit N-1 path when that round is non-degraded.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_8

### FINDING_8: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:997-1026
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Persisted degraded-retry.flag and degraded-retry.done can block a fresh retry when the same round directory is reused. A resumed or re-run Step 5 for the same round sees the banner but skips the inner retry branch, leaving degraded_this_round=true without a second core invocation. Clear retry markers at round entry or scope them to a run id so stale markers cannot suppress retries.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_9

### FINDING_9: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:951-1510
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Test matrix exceeds stated 8 regression tests in feature brief Higher harness maintenance than requested scope Trim to eight focused cases or update the spec to match the expanded matrix
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

