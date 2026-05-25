### FINDING_7: Empty-merge docs omit no-attestation zero-output path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The empty-merge documentation omits the validator path for zero output with missing attestation and no preamble. Operators may incorrectly expect all empty merges to produce narrow-trigger retry tokens and advance the waterfall, while no-attestation and pseudo-heading cases remain single-shot validation failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

