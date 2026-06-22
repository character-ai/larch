### OOS_1: [OUT_OF_SCOPE] Codex non-contiguous merge breaks positional tail mapping
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: When Codex combine runs before `issue_cap` with `cap >= 2`, the tail heuristic at `python/oos_filer.py:171-181` still assumes positional alignment between original `blocks` and the capped combined file. Codex can merge non-contiguous originals, so `blocks[combined_count-1:]` may over- or under-attach stable IDs on the aggregate issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Only if this path matters in production: derive stable IDs from combined-to-source correspondence (e.g. metadata from combine/cap) instead of slice position; or skip Codex when cap-driven rollup is expected.


