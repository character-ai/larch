### FINDING_1: implement PR resolution accepts design chore PRs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `--skill=implement` PR resolution can include design chore PR titles in list forms and single-PR forms, causing mapping/scanning against the wrong or empty implement run directories. The implement skill predicate should exclude design chore titles consistently in `filter_prs_for_skill` and `pr_matches_skill`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_2: duplicated skill enum validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Multiple scripts duplicate `--skill` enum validation, making future enum or message changes require lockstep edits across audit-runs and report-tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: duplicated design PR title matching logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Design PR title matching and UUID extraction are duplicated across resolve and map code, creating drift risk between filtering and mapping behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] audit-runs scan documentation overstates design scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The audit-runs SKILL scan table documents the full implement scan set without clearly distinguishing that design runs currently use the `scans-design.tsv` L1 cache-freshness subset. Operators may expect EXON/OOS scans for design audits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: audit-scan-run contract overstates cross-registry scan availability
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The scan-run contract implies all scan names exist across both implement and design registries, while the design registry currently defines only cache-freshness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: design audits emit partial category-stats unnecessarily
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Design-only audit batches mark `CATEGORY_STATS_PARTIAL=true` when `review-findings-full.jsonl` is absent, even though design scans currently do not require the implement review findings data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: preflight title-matcher consumer claim is inaccurate
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The plan says preflight consumes `audit-title-matcher`, but `audit-preflight.sh` does not source or call it. Current behavior is label-wide concurrency matching, so the plan/acceptance text is inaccurate unless skill-scoped matching is implemented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: missing tests for design PR filtering across verbal forms
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Hermetic tests do not cover design merged-PR title filtering for last-N and since-ISO forms, including interleaved implement/design merge titles. A filter-order or missing-filter regression could audit implement PRs during design runs without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: missing focused legacy prior discovery tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Implement since-last-audit backward compatibility for legacy `[Run Logs Audit]` titles is only indirectly covered. Tests do not assert the selected legacy `PRIOR_REPORT_NUMBER`, nor coexistence/disambiguation with prefixed implement priors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: missing report-tokens cross-skill plot-from rejection test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests cover design rejecting legacy `[Analysis Report]`, but do not cover implement `--plot-from` rejecting `[Design Analysis Report]` titles. The symmetric cross-skill guard in `run-analysis.sh` could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: audit-title.sh missing from skill enum rejection sweep
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: New `--skill` enum rejection tests cover other entrypoints but omit `audit-title.sh`, allowing inconsistent title-generation CLI validation to slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] repo token validation remains loose
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `--repo` / `LARCH_REPORT_TOKENS_REPO` are not validated as strict `owner/name` tokens before `gh` / `gh api`. Malformed values fail at the CLI rather than enabling injection, but strict validation would be cleaner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] concurrency guard is label-wide across skills
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The 5-minute audit concurrency guard is label-wide on `audit-report`, so a design audit can block an implement audit and vice versa unless `--allow-concurrent` is used. This may be intentional, but should be documented or made skill-scoped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] plot-from parses uncapped issue-body JSON
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `--plot-from` parses arbitrary JSON from fetched issue bodies. Title gating limits accepted issues, but body/fence size is not capped before `json.loads`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: design last-N filters after repo-wide slicing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Design last-N PR resolution slices the repo-wide last N merged PRs before applying the design title filter. Recent implement merges can cause design runs to return empty or fewer-than-requested design PRs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] category-stats emitted for design-only registry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Category stats are emitted after registry execution even for design-only scans, producing partial category-stats when `review-findings-full.jsonl` is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: design PR UUID regex allows lowercase despite uppercase-only plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Design PR title matching accepts lowercase hex UUID characters, while the plan acceptance specifies uppercase-only `[0-9A-F-]+`. Lowercase design run titles can be included and mapped despite the stated contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
