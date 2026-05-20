### FINDING_1: **Important** `correctness` `skills/review/scripts/review-core.sh:509` — Round 2+ votes are now intentionally 2-judge, but `tally-code-votes.sh` still emits `⚠ Degraded code-review panel` whenever effective voters are below 3 (`skills/review/scripts/tally-code-votes.sh:265-267`). Concrete failing scenario: round 2 launches Claude+Cursor successfully, `voting-tally.md` gets a degraded banner, then `review-and-fix.sh` sees that banner (`skills/review-and-fix/scripts/review-and-fix.sh:1005-1039`), retries the panel, and records `DEGRADED_ROUND=true`, which inflates round caps and excludes the round from convergence. Pass the round or expected voter count into `tally-code-votes.sh` and only emit the degraded banner when effective voters fall below the expected count for that round; add a round-2 regression test.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `skills/review/scripts/review-core.sh:509` — Round 2+ votes are now intentionally 2-judge, but `tally-code-votes.sh` still emits `⚠ Degraded code-review panel` whenever effective voters are below 3 (`skills/review/scripts/tally-code-votes.sh:265-267`). Concrete failing scenario: round 2 launches Claude+Cursor successfully, `voting-tally.md` gets a degraded banner, then `review-and-fix.sh` sees that banner (`skills/review-and-fix/scripts/review-and-fix.sh:1005-1039`), retries the panel, and records `DEGRADED_ROUND=true`, which inflates round caps and excludes the round from convergence. Pass the round or expected voter count into `tally-code-votes.sh` and only emit the degraded banner when effective voters fall below the expected count for that round; add a round-2 regression test.
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: scripts/test-dispatch-code-voters.sh:7-17
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness header still documents 11 scenarios and happy=scenarios 1-3. The happy section now includes a fourth round-2 scenario; comments mislead triage of CI shards and local --section usage. Refresh scenario counts and the happy section description to include the round-2 case.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: docs/voting-process.md:26
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] JUDGE_ERROR sentence still hardcodes a 3-judge panel after the doc now describes 2-voter rounds 2+ for /review. Readers can mis-parse how parse failures interact with tiering on rounds after the first. Reword to reference eligible voters or round-specific panel size instead of “3-judge.”
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: skills/review/scripts/test-check-reviewer-failure-threshold.sh:116-139
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New round-2+ threshold tests only exercise --panel hard. check-reviewer-failure-threshold.sh applies STATIC_INTENDED_SLOTS=6 to simple and hard for ROUND_NUM>1; a simple-only regression could ship while CI stays green. Add at least one simple --round-num 2 threshold case (INTENDED_SLOTS/FAILED_SLOTS/THRESHOLD_OK) parallel to the hard cases.
- **Suggested revision**: Address the concern above.


### FINDING_8: code-quality: docs/voting-process.md:26
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] JUDGE_ERROR note still hard-codes 3-judge panel Round 2+ /review is intentionally 2-judge; readers may think parse rules always assume a 3-judge shape Generalize to 2- and 3-judge /review or scope the sentence to contexts where three judges are always intended
- **Suggested revision**: Address the concern above.


