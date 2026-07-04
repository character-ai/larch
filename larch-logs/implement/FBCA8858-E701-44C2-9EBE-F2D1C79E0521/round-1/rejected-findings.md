### [rejected] FINDING_2

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_2: empty-stdout dynamic fallback reuses stale sidecar
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Dynamic review dispatch can fall back to the agent-file path when stdout is empty but still consume an old payload sidecar, so fallback prompts inherit stale `payload_bytes` and distort byte ranking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

