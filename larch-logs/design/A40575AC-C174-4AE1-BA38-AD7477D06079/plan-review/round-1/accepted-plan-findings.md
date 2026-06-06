### FINDING_1: emit-tally overwrites tally-written accepted OOS via oos-serialize
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: On the production review path, `tally-code-votes.sh` can write accepted OOS (including scope-drift reclassifications with bare `### FINDING_N:` headers) into `oos-accepted-review.md`, but `review-core.sh` always invokes `emit-tally.sh` next, which unconditionally calls `oos-serialize.sh` on `oos.md` and overwrites that sink. `oos-serialize.sh` only emits `### FINDING_N:` blocks tagged `[OUT_OF_SCOPE]` or `[OOS]` and does not rewrite headers to `### OOS_N:`; scope-drift accepted OOS (bare `### FINDING_N:`) are dropped. `review-core.sh` then propagates the overwritten file via `copy_to_parent`. Tally-only harness tests do not exercise this chain, so a plan that only normalizes tally output still fails acceptance in production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make emit-tally preserve tally output when OOS_ACCEPTED_COUNT>0 (skip oos-serialize), or apply the same normalize_oos_block_header logic inside oos-serialize and include scope-drift blocks; add a review-core/emit-tally integration assertion for scope-drift and [OUT_OF_SCOPE] accepted paths
  - From Cursor-Requirements: Add emit-tally.sh and/or oos-serialize.sh to the plan: skip oos-serialize when tally already wrote accepted OOS (e.g. OOS_ACCEPTED_COUNT>0), or apply the same normalize_oos_block_header logic inside oos-serialize and include scope-drift accepted blocks; add a review-core/emit-tally integration assertion for [OUT_OF_SCOPE] and scope-drift accepted paths


### FINDING_2: Dual-sink write must preserve OOS_ACCEPTED_OUT != OOS_ACCEPTED_FILE guard
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: When `SESSION_ENV_PATH` is unset, `OOS_ACCEPTED_OUT` is set equal to `OOS_ACCEPTED_FILE` (lines 111–115). The current code appends accepted blocks once to `OOS_ACCEPTED_FILE` and only mirrors to `OOS_ACCEPTED_OUT` when the two paths differ. A plan that pipes normalized output into both sinks unconditionally would duplicate every accepted block in standalone review mode, inflate awk/Python `non_security` counts, and can false-fail the disposition gate (two blocks needing coverage for one accepted finding).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Preserve the current branch: append normalized output once to OOS_ACCEPTED_FILE, then append to OOS_ACCEPTED_OUT only when OOS_ACCEPTED_OUT != OOS_ACCEPTED_FILE; optionally assert awk count == 1 in single-OOS harness cases to catch regressions

---

**Merge rationale**: FINDING_1 and FINDING_3 from the inputs describe the same production overwrite chain (`tally-code-votes` → `emit-tally` → `oos-serialize` → `copy_to_parent`) and the same failure mode for scope-drift accepted OOS; they differ only in wording. FINDING_2 is a separate risk on the tally write path (dual-sink duplication when paths alias) and stays distinct because it needs a different fix (equality guard), not emit-tally/oos-serialize changes.

