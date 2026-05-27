## Proposed Design Outline

### Goals
- Add `make test-stall-recovery-report` row to `docs/linting.md` harness inventory table (Item B).
- Consolidate 46 duplicated `awk LARCH_CLAUDE_PLUGIN_ROOT=` rehydration blocks in `skills/implement/SKILL.md` Step 18 (Item C).
- Fix `skills/design/SKILL.md:375` reference from "Step 5c item 9" to "Step 5c item 10" (Item G).

### Non-goals
- Touching Items A, D, E, F — re-verified as already addressed in `main`.
- Touching Items H, I, J — reference a "Step 3.6 plan-quality assessor" feature that does not exist in the tree.
- Behavioral, contract, or test changes — doc-only sweep.

### Approach sketch
- Item B: add one row to the harness table near line 177 of `docs/linting.md` describing the offline harness and its CI shard.
- Item C: extract the canonical rehydration block to a helper script (`scripts/rehydrate-claude-plugin-root.sh` or sourceable `.inc.bash`) and replace each of the 46 sites with a one-line invocation; OR define the snippet once as a top-of-file Bash fragment and reference it via a comment anchor. Pick the path that minimizes Bash-block churn and survives the existing `lint-foreground-markers` / `lint-bash32` linters.
- Item G: single-token edit at `skills/design/SKILL.md:375`.

### Surfaces in scope
- `docs/linting.md`
- `skills/implement/SKILL.md` (Step 18 region)
- `skills/design/SKILL.md` (line 375 only)
- Possibly `scripts/` (new helper for Item C if the script approach is taken)

### Open questions
- Item C: in-SKILL anchor + textual reference vs. extracted shell helper sourced from each site. The plan will decide based on which approach changes the fewest Bash fences and keeps lint markers intact.
