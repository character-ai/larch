# Review Round 4

- Mode: `diff`
- 6 accepted, 6 rejected (6 exonerated)

## Accepted Findings

### FINDING_1: implement PR resolution accepts design chore PRs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `--skill=implement` PR resolution can include design chore PR titles in list forms and single-PR forms, causing mapping/scanning against the wrong or empty implement run directories. The implement skill predicate should exclude design chore titles consistently in `filter_prs_for_skill` and `pr_matches_skill`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.


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


### FINDING_15: design last-N filters after repo-wide slicing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Design last-N PR resolution slices the repo-wide last N merged PRs before applying the design title filter. Recent implement merges can cause design runs to return empty or fewer-than-requested design PRs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


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


