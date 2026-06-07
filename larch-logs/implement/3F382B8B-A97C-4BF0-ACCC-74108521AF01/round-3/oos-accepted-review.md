### OOS_12: [OUT_OF_SCOPE] Cumulative accepted findings can duplicate logical findings and inflate counts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt, dyn-artifact-state-output.txt, dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: In-scope cumulative accumulation concatenates blocks without consistent deduplication, so repeated logical findings across rounds can inflate final summary accepted counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt, dyn-artifact-state-output.txt, dyn-bash-portability-output.txt: Address the concern above.


### OOS_13: [OUT_OF_SCOPE] Multi-round integration and pause/resume coverage is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt, dyn-artifact-state-output.txt
- **Severity**: nit
- **Concern**: Existing harnesses do not exercise a full Step 3 → Gate B → continuation → Step 3 loop or pause-during-auto-continuation behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt, dyn-artifact-state-output.txt: Address the concern above.


### OOS_14: [OUT_OF_SCOPE] render-final-summary array expansion lacks defensive Bash 3.2 idiom
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: The new array expansion does not use the safe-empty idiom, though an existing `-s` guard makes this a minor defensive-style gap rather than a demonstrated regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.


### OOS_15: [OUT_OF_SCOPE] SECURITY.md still describes Step 3 as single-pass
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: SECURITY.md may understate the new heuristic multi-round behavior and its trust-boundary implications.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### OOS_16: [OUT_OF_SCOPE] Single Important finding triggers continuation despite implement threshold
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt, dyn-artifact-state-output.txt
- **Severity**: important
- **Concern**: `/design` continues on any important accepted finding, while the intended `/implement` symmetry requires at least two important findings or other substantial-change signals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt, dyn-artifact-state-output.txt: Address the concern above.


