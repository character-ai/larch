### FINDING_5: cap_hit regression does not model sentinel-only output
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The `cap_hit` grouped test uses stub output containing `## Recommendation`, while launcher `cap_hit` can produce sentinel-only files; the test may miss regressions for that production shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


