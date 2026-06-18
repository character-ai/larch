### OOS_1: [OUT_OF_SCOPE] Filed production timeline still not fixed by pointer mtime alone
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The reported production timeline (older active session, newer failed bootstrap pointer) is not addressed by pointer-mtime-only selection. Both old and new heuristics can prefer the ~3m-old failed session over the ~2h Step 5 session when its pointer is newer. Plan documents this as an accepted failure mode unless addressed via pointer teardown/hygiene or hybrid ranking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


