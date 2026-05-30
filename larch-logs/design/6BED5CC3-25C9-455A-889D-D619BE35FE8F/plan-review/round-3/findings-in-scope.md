Two independent correctness risks (grep option parsing vs trailer `block_len` / plan-size testing). No merge warranted.

### FINDING_1: BSD/macOS grep treats `--flag` patterns as options
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Proposed (3175) greps use `grep -Fq '--snapshot-trailers'` / `grep -Fq '--dedup'` without a pattern terminator. On BSD/macOS (and the repo’s harness style), grep treats a leading-`--` pattern as an option; the pin aborts with `unrecognized option` before the structural test runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Use `grep -Fq -- '--snapshot-trailers'` and `grep -Fq -- '--dedup'` (or the existing `contains()` helper at `scripts/test-design-structure.sh:23-25`) for each new literal hook pin

### FINDING_2: Missing parse-mode fixture for duplicate strict trailers vs `block_len`
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Testing strategy omits a parse-mode fixture where duplicate strict trailer lines make `block_len` differ from present-key count. In `parse`, line 1 is `block_len` (physical metadata lines); `check-plan-size.sh` subtracts it for `plan_lines`. Reverting `metadata_trailer_lines = block_len` to a present-key sum (e.g. two `diff_added:` lines → `block_len` 2 vs metric 1) can pass last-match-wins `values`/`has_key` cases and still break plan-size gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a fixture with duplicate `diff_added:` (or mixed duplicate trailers) in the final block; assert `parse` line 1 equals the physical line count; list it under Edge cases and Testing strategy
