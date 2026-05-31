### [Plan Review] FINDING_3

### FINDING_3: Timing-rehydration test assertion (b) may not match post-migration SKILL fence shape
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `scripts/test-implement-timing-rehydration.sh` assertion (b) at lines 128–132 counts exact standalone lines via `grep -Fxc` for `  CLAUDE_PLUGIN_ROOT=$(awk ...`. If the same PR migrates pre-bootstrap fences in `skills/implement/SKILL.md` (e.g. lines 105–108, 307–311, 466–469) to a single compound line starting with `[` with `CLAUDE_PLUGIN_ROOT=$(awk` embedded after `&&`, the literal-line count drops (possibly to 0 or ≠ expected parity) while Invariant C’s awk fence scan may still pass—so `make test-implement-timing-rehydration` fails or parity is lost without a detector aligned to the new template.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After SKILL migration, awk-extract grep count is 0 (or not 3); `make test-implement-timing-rehydration` fails or the parity check is retired without a replacement that matches the new shape In the same PR, change assertion (b) to count lines containing `CLAUDE_PLUGIN_ROOT=$(awk` and `LARCH_CLAUDE_PLUGIN_ROOT=` (or match the exact compound-line template), and align `test-implement-timing-rehydration.md` invariant 4 / Invariant C with that detector

**Merge notes (for voters, not machine fields):**
- Input FINDING_1 and FINDING_2 share one behavioral risk (sourced writer pollutes bootstrap shell options / abort semantics); merged into aggregated FINDING_1 with max severity **important**.
- Input FINDING_3 is a distinct contract (`return` vs `exit` inside the helper); kept as aggregated FINDING_2.
- Input FINDING_4 is an independent test/SKILL parity risk; kept as aggregated FINDING_3.
- No `[OUT_OF_SCOPE]` tags in the supplied inputs; no `### OOS_N:` blocks.

