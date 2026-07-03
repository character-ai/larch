## Proposed Design Outline

### Goals
- Split each committed `panel-prompt-sizes.tsv` row's `prompt_bytes` into `scaffold_bytes` (builder-generated fixed instruction text) and `payload_bytes` (irreducible per-run content: inlined plan text, diff, issue/feature body) for every slot kind (specialist, plan-review, voter, aggregator, implementer).
- Extend `measure-panel-cost` to rank sources by realized scaffold bytes, giving the three already-filed density-pass children (#6159, #6160, #6161) an honest compression target.
- Document the new columns in `docs/run-logs.md`.

### Non-goals
- No prose compression of any scaffold text itself — that is the three density-pass children's job, not this issue's.
- No change to protocol grammars, dispatch behavior, panel topology, or vote/finding output shape.
- No backfill or migration of historical committed `panel-prompt-sizes.tsv` rows; new columns apply going forward only.

### Approach sketch
- Add `scaffold_bytes`/`scaffold_tokens`/`payload_bytes`/`payload_tokens` to `PanelPromptSizeRow` and `append_panel_prompt_size()` in `python/larch/report/tokens.py`; callers supply `payload_bytes`, the function derives scaffold as the remainder.
- Render-time builders (`rendering.py`'s `render_plan_review_main` / `render_specialist_main` / `render_voter_main`) gain an optional `--payload-bytes-output <path>` sidecar so each builder — the only place that knows whether plan/feature/scope-anchor content was actually inlined for a given vendor, versus just path-referenced — reports its own accurate payload byte count.
- Manifest-building call sites that pre-render prompts ahead of dispatch (`plan_review_panel.py`, `review_dispatch_panel.py`'s dynamic-archetype path, `review_aggregate.py`) capture that count into the manifest row; `agent_waterfall.py`'s `Slot` plumbing and `_review_launcher.py` / `_claude_runner.py` forward it to the eventual `append_panel_prompt_size` call. Same-process paths (static specialist rows rendered on demand at dispatch time) pass it directly with no manifest hop.
- `coder_runner.py`'s implementer prompt computes payload bytes locally (scrubbed findings-file size) since it composes its prompt in-process without a `render` subprocess.
- Extend `measure_panel_cost()` aggregation with the new columns and change its sort key to rank by scaffold bytes descending.

### Surfaces in scope
- `python/larch/report/tokens.py`
- `python/larch/rendering/rendering.py`
- `python/larch/review/plan_review_panel.py`
- `python/larch/review/review_dispatch_panel.py`
- `python/larch/review/review_aggregate.py`
- `python/larch/review/coder_runner.py`
- `python/larch/agents/agent_waterfall.py`
- `python/larch/agents/_review_launcher.py`
- `python/larch/agents/_claude_runner.py`
- `docs/run-logs.md`

### Open questions
- None.
