## Proposed Design Outline

### Goals
- Port 8 bash scripts (decompose, scout, scope-anchor, findings-classification) to Python with importable functions and CLI verbs.
- Direct call-site cutover across all callers (including `dispatch-panel.sh`); no shims.
- pytest replaces bash harnesses; absorbed bash + `.md` siblings deleted; stale-reference sweep done.

### Non-goals
- Does not port `dispatch-with-waterfall.sh` or other bash dependencies the new Python code calls.
- Does not change protocol/behavior; pure sh-to-py port.
- Does not create intermediate shim `.sh` files.

### Approach sketch
- Add `python/decompose.py` — absorbs decompose-file-issues.sh, decompose-panel-dispatch.sh, decompose-aggregator.sh; CLI domain `decompose`.
- Add `python/plan_scout.py` — absorbs scout-plan-archetypes-wrapper.sh, scout-dynamic-archetypes.sh; CLI domain `scout`.
- Extend `python/rendering.py` — absorbs render-main-agent-scope-anchor.sh and lib-scope-anchor-handoff.sh (partial logic already present); CLI verbs `render scope-anchor` and `scope-anchor relay-allowed` / `scope-anchor validate`.
- Extend `python/voting.py` — absorbs lib-findings-classification.sh (one function); CLI verb `voting findings-classification-header`.
- Update all call sites: `dispatch-panel.sh`, `plan-review-loop.sh`, `tally-plan-review.sh`, `persist-retally-step3-env.sh`, `launch-codex-drafter.sh`, `launch-claude-drafter.sh`, `dispatch-plan-review-panel.sh`, `decompose-panel.md`, SKILL.md references.
- Add entries to `python/migrated-scripts.tsv`; run `make lint-retired-scripts`.

### Surfaces in scope
- `python/decompose.py`, `python/test_decompose.py` (new)
- `python/plan_scout.py`, `python/test_plan_scout.py` (new)
- `python/rendering.py`, `python/test_rendering.py` (extended)
- `python/voting.py`, `python/test_voting.py` (extended)
- `python/cli.py` (new registry entries)
- `python/migrated-scripts.tsv` (new rows)
- `skills/design/scripts/decompose-*.sh` + `.md` + test harnesses (deleted)
- `skills/design/scripts/scout-plan-archetypes-wrapper.sh` + siblings (deleted)
- `skills/design/scripts/render-main-agent-scope-anchor.sh` (deleted)
- `skills/design/scripts/lib-findings-classification.sh` + `.md` (deleted)
- `scripts/scout-dynamic-archetypes.sh` + `.md` + `test-scout-dynamic-archetypes.sh` (deleted)
- `scripts/lib-scope-anchor-handoff.sh` + `.md` (deleted)
- Call-site updates: `dispatch-panel.sh`, `plan-review-loop.sh`, `tally-plan-review.sh`, `persist-retally-step3-env.sh`, `launch-codex-drafter.sh`, `launch-claude-drafter.sh`, `dispatch-plan-review-panel.sh`, `decompose-panel.md`, SKILL.md

### Open questions
- None.
