### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-render-cost-line-callsites.sh:84
- **Concern**: Step 5d harness grep needle not explicitly retargeted when prose compacts. Scenario: The plan compacts Step 5d emit prose to a pointer while keeping only a compact post-driver gate phrase in skills/design/SKILL.md, but the harness retarget section does not explicitly require replacing the line 84 grep for the long needle marker extraction after driver handoff (`_publish_rc` 0, 1, or 3), with a non-empty `$DESIGN_TMPDIR/final-summary.md` or parsed `FINAL_SUMMARY_PATH` Read fallback. A prior similar refactor left this harness stale while SKILL prose changed and make lint failed even when behavior was correct.
- **Proposed resolution**: Under ### UPDATED: scripts/test-render-cost-line-callsites.sh, add an explicit step: replace the line 84 grep target with the new compact Step 5d gate phrase (or a stable substring of it), and retire the long marker extraction after driver handoff needle from the design SKILL grep surface.

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-render-cost-line-callsites.sh:84-84
- **Concern**: Step 5d harness pin not updated for compact-pointer dedup. Scenario: The plan requires Step 5d to drop the long marker/fallback restatement for a compact pointer to skills/shared/final-summary-emit.md (marker-first profile), but still lists keeping the Step 5d post-driver gate pin in skills/design/SKILL.md without telling scripts/test-render-cost-line-callsites.sh to replace the line 84 grep. That grep still requires the retired sentence marker extraction after driver handoff (`_publish_rc` 0, 1, or 3), with a non-empty `$DESIGN_TMPDIR/final-summary.md` or parsed `FINAL_SUMMARY_PATH` Read fallback. After dedup, either the harness fails make lint or the author keeps the old prose and acceptance fails (instruction still appears more than once).
- **Proposed resolution**: In scripts/test-render-cost-line-callsites.sh, replace the line 84 exact-string grep with a pin on the new compact Step 5d gate (pointer to skills/shared/final-summary-emit.md plus `_publish_rc` 0/1/3 and no-recap ordering), and document the retired long sentence in scripts/test-render-cost-line-callsites.md.
