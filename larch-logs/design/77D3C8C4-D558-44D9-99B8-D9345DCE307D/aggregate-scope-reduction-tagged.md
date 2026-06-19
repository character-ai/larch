### FINDING_7:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/plan_review_tally.py; python/review_tally.py; skills/design/scripts/design-step3-mav.sh:279-284
- **Concern**: [SCOPE-REDUCTION] The plan adds implicit proposer-map defaulting when the flag is omitted instead of updating every production re-tally caller to pass the sidecar explicitly. Scenario: A legacy or direct tally call in a tmpdir that already contains proposer-map.tsv can silently score a different ballot with stale proposer labels. The current design-step3-mav.sh re-tally call omits the sidecar flag, so the plan depends on that risky implicit default for the /design MAV path
- **Proposed resolution**: Remove implicit sidecar defaulting. Keep omitted --proposer-map-file as legacy ballot parsing only. Add skills/design/scripts/design-step3-mav.sh and its tests to the plan, and pass --proposer-map-file "$DESIGN_TMPDIR/proposer-map.tsv" when present; keep review core and Step 5 MAV explicit too.
