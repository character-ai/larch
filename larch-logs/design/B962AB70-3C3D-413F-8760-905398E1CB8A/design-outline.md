## Proposed Design Outline

### Goals
- Consolidate Step 5c into one in-process Python surface: a new `step5c` entrypoint in `python/design_lifecycle.py` that runs both the wrapper orchestration and the publish tail, with no subprocess hop.
- Reduce `skills/design/scripts/design-step5c.sh` to a thin delegation wrapper.
- Preserve the `SKILL.md` orchestrator contract exactly: stdout machine rows, `LARCH_FINAL_SUMMARY_*` body, `REPORT_GATE_SIDECARS_FILE=`, sentinels, status env, and publish exit-code semantics.

### Non-goals
- No change to publish behavior or wire format: provenance splice, redaction, `named-block write --marker plan`, diagrams upsert, `[DESIGNED]` rename, `log-publish`, secret-scrub warning.
- No change to how `SKILL.md` invokes the wrapper or parses its output.
- No change to Step 5b, Step 6, `render-final-summary`, or `review_provenance` behavior.

### Approach sketch
- Add `step5c_main` to `python/design_lifecycle.py`, porting `design-step5c.sh` orchestration (preconditions, `.pause-requested` exec, `.bg-wait-active` try/finally, abort + `stage-terminal-state`, result-env parse, sentinels, `.design-step5c-status.env`, marker emission, final-summary render) following the existing `step_final_summary_main` pattern.
- Run the publish tail in-process by calling the existing publish logic directly instead of `cli.py design publish`.
- Keep `python/design_publish.py` as the in-process publish library (preserves `review_provenance` for `design_summary.py` and the 14 existing tests); refactor `publish_main` so its core is callable in-process.
- Add `("design","step5c")` to `cli.py` rows + allowlist; wrapper delegates to it.
- Add Step 5c orchestration tests to `python/test_design_lifecycle.py`; retain `python/test_design_publish.py`.

### Surfaces in scope
- `python/design_lifecycle.py`, `python/design_publish.py`, `python/cli.py`
- `skills/design/scripts/design-step5c.sh` + `design-step5c.md`, `skills/design/scripts/test-design-step5c.sh`
- `python/test_design_lifecycle.py`, `python/test_design_publish.py`, `python/checks.py`
- Verb-reference docs: `skills/design/SKILL.md`, `skills/design/references/flags.md`, `docs/run-logs.md`

### Open questions
- Consolidation depth: call `design_publish.py` in-process and keep it as a library (recommended, minimal churn, keeps `review_provenance` + tests stable) vs physically merge it into `design_lifecycle.py` and delete the module. The plan will pick the in-process-library path unless you prefer the full merge.
- Fate of the public `("design","publish")` verb: keep as internal/legacy vs remove (only caller is the wrapper). Plan defaults to keeping it.
