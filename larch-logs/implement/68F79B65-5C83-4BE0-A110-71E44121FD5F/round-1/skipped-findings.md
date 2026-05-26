### FINDING_32: correctness: skills/design/scripts/test-tally-plan-review.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan mandates 13 new tally harness cases; script unchanged. Acceptance-listed tally regressions (mutex stderr exact text out flag MainAgent 21-field sanitization) are not exercised on test-tally-plan-review.sh. Implement the 13 cases in test-tally-plan-review.sh or revise acceptance to a single harness with explicit mapping.
- **Suggested revision**: Address the concern above.



### FINDING_35: correctness: skills/design/scripts/test-plan-review-loop.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Loop harness lacks middle-slot failure and full zero-exit TSV coverage. VOTER_2_STATUS=failed compaction and panel-failed header-only TSV paths are unverified; tally --voter argv not inspected. Stub failed slot 2 assert v2 empty v3 filled assert TSV on panel-failed optionally log tally argv.
- **Suggested revision**: Address the concern above.



