### OOS_1: [OUT_OF_SCOPE] Branch fixes #4884 via report reframing, not concern-level suppression
- **Reviewer(s)**: dyn-design-flow-output.txt, dyn-report-framing-output.txt
- **Severity**: latent
- **Concern**: The branch reframes rejected-findings output and hardens prompts but does not add semantic/plan-text overlap filtering. Findings that re-raise already-implemented concerns with different dedup keys can still appear under the new heading. That matches the attached plan's "output hygiene, not semantic suppression" approach, but it does not fully close the original bug's root cause (e.g. the 5/7 false positives noted in #4884).
- **Suggested revisions (informational for voters; coder decides)**:


