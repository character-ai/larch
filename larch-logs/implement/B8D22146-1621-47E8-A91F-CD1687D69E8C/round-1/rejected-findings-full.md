### [rejected] FINDING_13

### FINDING_13: correctness: scripts/dispatch-code-voters.sh:163-239 (launch_voter_retry / check_and_retry_voter_parse_rate)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Retry stderr sidecar ${retry_output}.launcher-stderr is not removed after mv promotes retry output to the canonical voter path. Stale *-parse-retry.txt.launcher-stderr files under REVIEW_TMPDIR can mislead debugging or accumulate clutter. rm -f retry sidecars after successful promotion (and optionally on failure if undesired).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_19

### FINDING_19: risk-integration: scripts/dispatch-code-voters.sh:140-149
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] append-tool-failure --tool string implies launch-${voter_tool}-review.sh for all tools. Codex/Cursor parse checks use launch-review.sh; logs point maintainers at the wrong launcher name. Match --tool to the actual launcher used per branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_6

### FINDING_6: architecture: scripts/dispatch-code-voters.md:37
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] DEGRADED_PANEL_WARNING text uses “effective judges” while tally uses EFFECTIVE_VOTERS with a different definition. Doc readers may equate dispatch KV semantics with tally’s EFFECTIVE_VOTERS and misread panel health. Reword to avoid overloading “effective” or cross-reference tally terminology explicitly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_9

### FINDING_9: code-quality: scripts/dispatch-code-voters.sh:215-231
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Successful retry mv leaves *-parse-retry.txt.launcher-stderr orphan. REVIEW_TMPDIR accumulates sidecar junk across runs. rm retry sidecars after successful promotion.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

