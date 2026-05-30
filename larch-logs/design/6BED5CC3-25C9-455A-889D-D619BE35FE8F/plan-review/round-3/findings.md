### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:38-39
- **Concern**: Proposed (3175) greps use `grep -Fq '--snapshot-trailers'` / `grep -Fq '--dedup'` without a pattern terminator. Scenario: On BSD/macOS (and the repo’s own harness style), grep treats a leading-`--` pattern as an option; the pin aborts with `unrecognized option` before the structural test runs
- **Proposed resolution**: Use `grep -Fq -- '--snapshot-trailers'` and `grep -Fq -- '--dedup'` (or the existing `contains()` helper at `scripts/test-design-structure.sh:23-25`) for each new literal hook pin

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-trailer-awk.sh (planned)
- **Concern**: Testing strategy omits a parse-mode fixture where duplicate strict trailer lines make block_len differ from present-key count. Scenario: `parse` line 1 is `block_len` (physical metadata lines); `check-plan-size.sh` subtracts it for `plan_lines`. Reverting `metadata_trailer_lines = block_len` to a present-key sum (e.g. two `diff_added:` lines → block_len 2 vs metric 1) can pass last-match-wins `values`/`has_key` cases and still break plan-size gating
- **Proposed resolution**: Add a fixture with duplicate `diff_added:` (or mixed duplicate trailers) in the final block; assert `parse` line 1 equals the physical line count; list it under Edge cases and Testing strategy
