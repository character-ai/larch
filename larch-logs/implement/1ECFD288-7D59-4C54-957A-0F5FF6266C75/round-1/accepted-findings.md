### FINDING_1: Cp-fail test couples to earlier dedup scenario
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The cp-failure regression test compares the cp-fail Codex launch counter against a counter from an earlier dedup scenario, so unrelated test reordering or happy-path launch-count changes can fail the harness without a production regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


