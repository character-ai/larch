### [rejected] FINDING_4

### FINDING_4: Documentation misstates fetch timing for the find-lock vs preflight callers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `scripts/check-main-sync.md` wording implies the wrong relative timing of fetch versus no-fetch callers, which can mislead operators about whether `origin/main` is fresh or stale on the find-lock path versus preflight.
- **Suggested revision**: Rewrite the sentence(s) so the documented fetch behavior matches each caller’s actual behavior.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

