### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: scripts/ship-pr.sh:1587-1594,scripts/create-pr.sh:130-254
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Nested transient retry: ship-pr wraps all of create-pr.sh while create-pr now wraps push and gh pr create internally. Sustained GitHub flake during /implement Step 9b can run up to 3 outer script retries each re-running 3 inner push and 3 inner create attempts with stacked 2s/4s backoff (~tens of seconds, duplicate push/create work). Keep retry at one layer for the ship-pr→create-pr chain (caller env gate or drop outer wrap; inner-only for standalone create-pr).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: risk-integration: scripts/test-design-log-publish.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required end-to-end transient gh pr create retry test is missing. After push succeeds, a one-shot transient API failure still leaves a remote branch; without a succeed-on-retry fixture, regressions in with_transient_retry around pr create would reintroduce the original non-fast-forward failure on operator retry. Add gh stub attempt counter: fail attempts 1-2 with transient stderr, succeed on 3; assert PUBLISH_OK=true and remote branch retained until merge.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: scripts/ship-pr.sh:3087-3088,scripts/merge-pr.sh:283-393
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Nested transient retry: ship-pr envelope wrapper around merge-pr.sh plus new inner fetch/merge wraps. CI-merge phase can multiply fetch and gh pr merge attempts beyond the plan’s 3-attempt intent and amplify latency during outages. Same single-layer rule: inner wraps for standalone merge-pr; outer ship_pr only when envelope predicate is needed, or vice versa.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/test-lib-net.sh:38-51
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Test harness duplicates ship_pr_with_transient_retry instead of testing ship-pr.sh’s copy. Future ship-pr wrapper changes can pass test-lib-net while breaking production envelope exhaustion. Share one definition or add an edit-in-sync contract test against ship-pr.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: risk-integration: scripts/tracking-issue-write.sh:398-418
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Wrapped gh issue comment can duplicate on retry after server success + lost response Lifecycle tracking issue shows duplicate marker comments Document tradeoff or add idempotent comment marker
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_31: risk-integration: scripts/rebase-push.sh:280-293
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Nested 3x3 transient retries on lease-race push loop Sustained outage extends Step 12c push wall-time materially Document or use single retry layer in lease loop
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_36

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_36: architecture: scripts/ship-pr.sh:2760-2762
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Post-rebump gh pr edit uses || true on the wrapper without the documented _WTR_RC read pattern. Matches plan wording literally but diverges from the set -e contract documented in lib-net.md. Capture rc via set +e and _WTR_RC, then ignore non-zero for best-effort semantics.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: scripts/ship-pr.sh:2760-2762
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Best-effort gh pr edit wrap ignores _WTR_RC per plan. Harder to extend logging/metrics on silent title-sync failures. Capture _WTR_RC then ignore, per lib-net.md Shape B.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: scripts/lint-awk-multibyte-regex.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Orthogonal 381-line linter bundled in retry PR. Harder bisect and review of retry-only changes. Split follow-up if not CI-blocking.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

