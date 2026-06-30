### OOS_1: [OUT_OF_SCOPE] No CI enforcement of stale complexity suppressions
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: Documentation in `python/ruff.toml` and `docs/linting.md:50-54` requires keeping production per-file complexity codes minimal against the regenerated baseline, but no linter mechanically enforces stale-suppression cleanup. Only the `complexity-baseline` regression ratchet and `make py-lint` guard over-pruning. Contributors can leave obsolete per-file complexity codes indefinitely without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Consider a future structural lint comparing baseline file/code sets to production complexity ignores.

### OOS_2: [OUT_OF_SCOPE] Dead `checks.py = []` per-file-ignores stub
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: `python/ruff.toml:236` retains a dead `"checks.py" = []` per-file-ignores entry with an empty ignore list after complexity codes were pruned. The plan calls for removing the whole entry when the post-prune list is empty; the stub is dead config with no CI effect (pre-existing in this diff).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Delete the checks.py = [] row from python/ruff.toml.

### OOS_3: [OUT_OF_SCOPE] Incomplete path qualification for duplicate basenames
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: Most production complexity ignores in `python/ruff.toml` still use basename keys; only `larch/cli.py` and `larch/issue/_report.py` were path-qualified. Future package splits that introduce shared basenames will still need manual path qualification, and duplicate production basenames across packages could inherit stale suppressions on a cleaned sibling file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Re-audit duplicate production basenames during the next split cleanup pass.

**Merge notes**
- FINDING_1 ↔ input FINDING_1 (edge-cases) + FINDING_5 (testing): same stale-suppression enforcement gap.
- FINDING_2 ↔ input FINDING_2 (edge-cases) + FINDING_4 (testing): same dead `checks.py = []` stub.
- FINDING_3 ↔ input FINDING_3 (edge-cases) + FINDING_6 (testing): same basename vs path-qualified maintenance risk.
- `cursor-specialist-edge-cases` findings had no concrete fix text beyond “Address the concern above,” so no `- From cursor-specialist-edge-cases:` bullets were added.

