### FINDING_12: [OUT_OF_SCOPE] repo token validation remains loose
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `--repo` / `LARCH_REPORT_TOKENS_REPO` are not validated as strict `owner/name` tokens before `gh` / `gh api`. Malformed values fail at the CLI rather than enabling injection, but strict validation would be cleaner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_13: [OUT_OF_SCOPE] concurrency guard is label-wide across skills
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The 5-minute audit concurrency guard is label-wide on `audit-report`, so a design audit can block an implement audit and vice versa unless `--allow-concurrent` is used. This may be intentional, but should be documented or made skill-scoped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_14: [OUT_OF_SCOPE] plot-from parses uncapped issue-body JSON
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `--plot-from` parses arbitrary JSON from fetched issue bodies. Title gating limits accepted issues, but body/fence size is not capped before `json.loads`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_16: [OUT_OF_SCOPE] category-stats emitted for design-only registry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Category stats are emitted after registry execution even for design-only scans, producing partial category-stats when `review-findings-full.jsonl` is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_4: [OUT_OF_SCOPE] audit-runs scan documentation overstates design scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The audit-runs SKILL scan table documents the full implement scan set without clearly distinguishing that design runs currently use the `scans-design.tsv` L1 cache-freshness subset. Operators may expect EXON/OOS scans for design audits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


