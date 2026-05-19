## Goal
Rebalance 16 test-harness CI shards using measured per-test timings and add --no-logs-commit to argument-hint listings

## Implementation Plan

### Part 1: Rebalance test-harness shards (issue #2319)

**Goal**: Reduce shard imbalance from 31s–1m53s range to within 15 seconds of each other, using measured per-test wall-clock timings with LPT bin-packing.

**Procedure** (per docs/linting.md "Refreshing harness shard balance"):

1. Extract all test target names from the 16 shard lines in Makefile (lines 33–64), excluding `test-harness-shards-coverage`.

2. For each target, run `make <target>` and capture the `LARCH_HARNESS_TIMING\t<name>\t<N.NNs>` row. Strip the trailing `s` from the third column to get decimal seconds.

3. Sum timings for any target that emits multiple rows with the same name.

4. Apply LPT (Largest Processing Time first) bin-packing into 16 bins:
   - Sort (seconds, name) pairs descending by seconds.
   - Repeatedly assign each item to the currently least-loaded bin.

5. Update ONLY the 16 `test-harnesses-N:` lines in Makefile (lines 33–64). Constraints:
   - Keep `test-harness-shards-coverage` as the first prerequisite on shard 12.
   - Each rule must stay on a single physical line (no backslash continuations).
   - Keep the `# Shard-12 leads with the partition-invariant guard` comment above shard 12.
   - No other Makefile changes.

6. Run `make test-harness-shards-coverage` to verify no tests are missing, duplicated, or orphaned.

**Files changed**: `Makefile` (16 shard lines only).

---

### Part 2: Add --no-logs-commit to argument-hint listings

**Goal**: Document `--no-logs-commit` in all argument-hint and argument listing surfaces where it is currently absent. The flag is already described in body text of both SKILL.md files; only the short hints/listings are missing it.

**Locations** (insert `[--no-logs-commit]` after `[--no-admin-fallback]` in each):

1. `skills/implement/SKILL.md` frontmatter `argument-hint:` (line ~4):
   - Current: `[--no-admin-fallback] [--no-dynamic-archetypes | --dynamic-archetypes <N>]`
   - After: `[--no-admin-fallback] [--no-logs-commit] [--no-dynamic-archetypes | --dynamic-archetypes <N>]`

2. `README.md` `/implement` row HTML `<td>` (line ~82):
   - Current: `[--no-admin-fallback] [--coder=claude|codex|cursor]`
   - After: `[--no-admin-fallback] [--no-logs-commit] [--coder=claude|codex|cursor]`

3. `README.md` `/fix-issue` row HTML `<td>` (line ~76):
   - Current: `[--no-admin-fallback] [--coder=&lt;value&gt;]`
   - After: `[--no-admin-fallback] [--no-logs-commit] [--coder=&lt;value&gt;]`

4. `docs/skills.md` `/implement` Arguments line (~91):
   - Current: `[--no-admin-fallback] [--coder=claude|codex|cursor]`
   - After: `[--no-admin-fallback] [--no-logs-commit] [--coder=claude|codex|cursor]`

5. `docs/skills.md` `/fix-issue` Arguments line (~81):
   - Current: `[--no-admin-fallback] [--coder=<value>]`
   - After: `[--no-admin-fallback] [--no-logs-commit] [--coder=<value>]`

**Files changed**: `skills/implement/SKILL.md`, `README.md`, `docs/skills.md`.

---


## Test plan

- `make test-harness-shards-coverage` — confirms all tests are accounted for in exactly one shard.
- `/relevant-checks` (pre-commit on changed files) — markdownlint, jsonlint, shellcheck, agent-lint.
