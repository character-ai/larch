# Review Round 3

- Mode: `diff`
- 1 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_2: Blanket dunder exemption skips custom multi-arg constructors
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The lint exempts every dunder method, not just fixed-signature protocol dunders. This skips custom constructors such as `python/tracking_issue.py:91` and `python/research.py:209`, which have multiple non-`self` positional parameters and are not included in the baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Replace the blanket dunder exemption with an explicit whitelist of fixed-signature protocol methods, and put any true external-contract exceptions in `keyword-only-exemptions.json` before regenerating the baseline.
