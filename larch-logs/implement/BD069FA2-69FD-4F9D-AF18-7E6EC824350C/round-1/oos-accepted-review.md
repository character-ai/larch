### OOS_1: [OUT_OF_SCOPE] correctness: pre-existing oos_filer tail-slice stable-ID heuristic
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Pre-existing tail-slice stable-ID heuristic in `python/oos_filer.py:171-181`; not modified by the tip commit. Non-contiguous Codex combine before `issue_cap` can over/under-attach stable IDs on the aggregate issue. Map stable IDs from combine metadata instead of positional slice when the Codex path is active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


