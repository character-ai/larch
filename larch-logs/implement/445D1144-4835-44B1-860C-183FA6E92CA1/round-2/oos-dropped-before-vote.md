### OOS_1: [OUT_OF_SCOPE] Panel artifact routing duplicated without shared resolver
- **Reviewer(s)**: dyn-dyn-panel-env
- **Severity**: latent
- **Concern**: Panel artifact routing is now implemented three times (`review_dispatch_panel.py`, `agent_voters.py`, `review_aggregate.py`) with only the first path having the `round-<N>/` subdirectory fallback. A shared resolver would reduce the chance of future producer drift when new dispatch entrypoints are added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-panel-env: A shared resolver (for example `resolve_panel_artifact_dir(review_tmpdir, round_num)`) would reduce the chance of future producer drift when new dispatch entrypoints are added.

### OOS_2: [OUT_OF_SCOPE] measure_panel_cost realized_bytes still double-counts embedded agent weight
- **Reviewer(s)**: dyn-dyn-panel-env
- **Severity**: latent
- **Concern**: `measure_panel_cost()` still sets `realized_bytes = prompt_bytes + agent_bytes` per row. For slots where the rendered prompt already embeds agent markdown, this double-counts agent file weight in aggregate rankings. That skews `token measure-panel-cost` output but does not block per-slot logging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-panel-env: `measure_panel_cost()` still sets `realized_bytes = prompt_bytes + agent_bytes` per row. For slots where the rendered prompt already embeds agent markdown, this double-counts agent file weight in aggregate rankings (round-1 FINDING_2, neutral). That skews `token measure-panel-cost` output but does not block per-slot logging.

### OOS_3: [OUT_OF_SCOPE] review_tally sibling panel-prompt-sizes.tsv auto-write misses round-local TSV
- **Reviewer(s)**: dyn-dyn-panel-env
- **Severity**: important
- **Concern**: Sibling `panel-prompt-sizes.tsv` auto-write only checks `Path(payload_file).with_name("panel-prompt-sizes.tsv")`. If specialists/aggregator rows live under `round-<N>/` while `review-panel-manifest` is logged from the run root, the extra batch write never fires and voter-only rows may be the only ones committed from the run-root TSV.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-panel-env: Sibling `panel-prompt-sizes.tsv` auto-write only checks `Path(payload_file).with_name("panel-prompt-sizes.tsv")`. If specialists/aggregator rows live under `round-<N>/` while `review-panel-manifest` is logged from the run root, the extra batch write never fires and voter-only rows may be the only ones committed from the run-root TSV.
