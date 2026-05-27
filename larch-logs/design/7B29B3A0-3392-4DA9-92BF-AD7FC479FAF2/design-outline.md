## Proposed Design Outline

### Goals
- Make `skills/design/scripts/render-final-summary.sh` rc=0 on macOS Bash 3.2 on all non-`cancelled-outline` paths so `$DESIGN_TMPDIR/final-summary.md` is created and the `larch:final-summary` post-publish emit contract holds end-to-end.
- Add regression coverage that prevents this Bash 3.2 nounset hazard from re-appearing at the `invoke_render` call site.

### Non-goals
- No refactor of `render-final-summary.sh` beyond the failing expansions and one explanatory comment.
- No edits to `scripts/render-run-summary.sh` or `scripts/render-cost-line.sh` (verified hazard-free by Step 1d codebase audit).
- No broader Bash 3.2 audit of unrelated `skills/design/scripts/*.sh` or `scripts/*.sh` files.

### Approach sketch
- Apply the safe-empty idiom `${arr[@]+"${arr[@]}"}` to the three at-risk expansions in `invoke_render`: `render_cost_args`, `note_args`, and the `COST_ARGS` source-array at line 304 (defense-in-depth even though control flow guarantees population).
- Add one comment line near the guarded line 338 expansion pointing at `BASH_AUTHORING.md §3` so future editors keep the idiom.
- Land a static-grep regression pin so future edits cannot regress the safe-expansion idiom at the `invoke_render` call site. Decide in Step 2b whether to extend `make lint-bash32` or add a dedicated sibling harness alongside `scripts/test-collect-agent-bash32.sh`.
- Land a dynamic test that runs `render-final-summary.sh --post-publish-only` under `/bin/bash 3.2` (skip-with-loud-message on Bash 4+) against a minimal `$DESIGN_TMPDIR` fixture with an `approved` outcome, asserting rc=0 and a non-empty `final-summary.md`.

### Surfaces in scope
- `skills/design/scripts/render-final-summary.sh` — three guarded expansions + one comment line in `invoke_render`.
- One static-grep regression site — either `make lint-bash32` (under `Makefile` + the lint script it shells out to) or a new `scripts/test-render-final-summary-bash32.sh` sibling alongside `scripts/test-collect-agent-bash32.sh`.
- One dynamic test — either a new `scripts/test-render-final-summary-bash32.sh` or extension of the existing `skills/design/scripts/test-render-final-summary.sh`.
- `skills/design/scripts/render-final-summary.md` sibling doc — update only if the contract surfaces (it documents the rc behavior on Bash 3.2).

### Open questions
- Static-grep host: extend `make lint-bash32` vs. dedicated sibling harness (mirroring `test-collect-agent-bash32.sh`). Step 2b will pick whichever follows the closest existing precedent.
- Dynamic-test host: new `scripts/test-render-final-summary-bash32.sh` (mirrors precedent at `scripts/test-collect-agent-bash32.sh`) vs. fold into existing `skills/design/scripts/test-render-final-summary.sh` with a Bash-3.2-only `case` branch. Step 2b will pick based on which file already runs cross-bash.
