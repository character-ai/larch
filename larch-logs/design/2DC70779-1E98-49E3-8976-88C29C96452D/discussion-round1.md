## Decision 1: Scope — which gaps to address
- **Question**: Should this PR address all 8 listed gaps, or a subset?
- **Resolution**: Address gaps 1–5 in this PR. Gap 8 is already resolved (docs use generic `test-harnesses-N`). Gaps 6 and 7 are documented limitations that require redesign; update the existing `## Limitations` section to mention them explicitly but don't implement them.
- **Source**: codebase

## Decision 2: Gap 8 stale-docs status
- **Question**: Is the "stale shard name" in `test-lint-bare-grep-probe.md` still present?
- **Resolution**: No. The file already says "one `test-harnesses-N` shard" and the Makefile assigns it to `test-harnesses-2`. No stale row remains.
- **Source**: codebase

## Decision 3: Gap 5 (duplicated argv walkers)
- **Question**: Is this a correctness bug or a maintenance risk?
- **Resolution**: Maintenance risk only. Dedup `has_parent_ascent_path` and `has_explicit_path` into a shared helper to reduce drift surface. Include in this PR as it's a small awk refactor.
- **Source**: codebase

## Decision 4: Gaps 6 and 7 disposition
- **Question**: Should multiline scanning (gap 6) and absolute-root bounding (gap 7) be implemented?
- **Resolution**: No. Both require significant redesign. Update `## Limitations` in `lint-bare-grep-probe.md` to document them explicitly. The awk-based line scanner is not changed.
- **Source**: codebase
