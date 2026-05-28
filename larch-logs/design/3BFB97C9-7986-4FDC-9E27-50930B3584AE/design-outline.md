## Proposed Design Outline

### Goals
- Stop an unclosed fence in `plan.txt` from suppressing `## Constraints` duplicate-preservation in the post-apply dedup pass.
- Add a regression test that fails on the current code and passes after the fix.

### Non-goals
- No changes to other `in_fence` toggle sites (`write-tally.sh`, `oos-serialize.sh`, `render-findings-batch.sh`, `lint-bare-grep-probe.sh`).
- No change to the dedup output schema, the surrounding shell wrapper, or any caller.
- No change to fence-language-tag handling for **balanced** fences.

### Approach sketch
- In `_run_post_apply_pipeline`'s Python heredoc inside `skills/design/scripts/plan-review-loop.sh`, replace the stateful `in_fence` toggle with a two-pass walk.
- Pass 1 scans every line, pairs each fence opener with its matching closer, and records the set of line indices truly inside a balanced fence; unmatched openers are treated as text.
- Pass 2 runs the existing dedup loop, querying the precomputed in-fence set instead of mutating state mid-loop.
- `inside_constraints` / `constraints_level` continue to track section state; only the fence-membership lookup changes.
- Add one focused test in `skills/design/scripts/test-plan-review-loop.sh` that constructs a plan with an unclosed fence followed by `## Constraints` and duplicate constraint bullets, runs the dedup helper, and asserts the duplicates survive.

### Surfaces in scope
- `skills/design/scripts/plan-review-loop.sh` (Python heredoc inside `_run_post_apply_pipeline`).
- `skills/design/scripts/test-plan-review-loop.sh` (one new case).
- `skills/design/scripts/plan-review-loop.md` (sibling doc; note fence semantics if not yet documented).

### Open questions
- None.
