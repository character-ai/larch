### [rejected] FINDING_17

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_17: Stale retired-script comments break `lint-retired-scripts`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retired basename `validate-research-output.sh` remains in tracked comments after `migrated-scripts.tsv` update. `make lint-retired-scripts` fails on `make lint` despite successful runtime cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Reword comment to Python CLI; sweep repo (incl. legacy_review_shell comment) until lint-retired-scripts is green.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

