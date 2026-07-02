## Decision 1: Instrumentation-only boundary
- **Question**: Does child 1 change any panel routing, or only capture and commit ratings?
- **Resolution**: Capture and commit only. `applied_tier` is computed and logged but drives no panel behavior in this issue. Panel tiering lands in the companion tiered-panels child.
- **Source**: issue

## Decision 2: Worked-examples corpus depth
- **Question**: Curate 9 real cited examples now, seed concise + defer curation, or rubric-only?
- **Resolution**: Seed a concise rubric plus a small worked-example set per tier now; structure it so calibration refreshes and expands it later. Keeps child 1 instrumentation-focused.
- **Source**: user (recommended default; operator away at Step 1c)

## Decision 3: Floors enforcement model
- **Question**: Deterministic committed path-glob list, or globs plus rater judgment for semantic categories?
- **Resolution**: One committed, reviewable path-glob manifest. Floors are pure-mechanical, matching the issue's "single mechanical exception." A related file outside the globs does not floor unless the manifest names it.
- **Source**: user (recommended default; operator away at Step 1c)

## Decision 4: One run-level difficulty-rating.json per run dir
- **Question**: Under /implement (which nests /review at Step 5), do the coder and the nested scout each write difficulty-rating.json, risking a collision in one run dir?
- **Resolution**: The run owner writes the single run-level `difficulty-rating.json`. /implement owns it (implement_tier from the coder, design_tier from the issue wire field). Standalone /review writes its own in `larch-logs/review/<run>/`. A nested /review does not overwrite the implement-owned run-level file; its scout rating still flows into round-level `round-meta.json` and `panel-manifest.ndjson`.
- **Source**: codebase (run-dir batch model in `python/larch/report/run_log_batch.py`)

## Decision 5: Wire field reuses the existing plan-block metadata convention
- **Question**: How does /design stamp the tier on the tracking issue for /implement to read?
- **Resolution**: Add a `difficulty: <TIER>` provenance line in the `larch:plan` block, inserted in the same zone as `review_status:` / `rounds_completed:` and before the final `diff_lines:` trailer, plus a `difficulty:<tier>` GitHub label. /implement reads it through the existing `allowed` metadata tuple and `_plan_review_meta_value` reader in `preflight.py`.
- **Source**: codebase (`docs/issue-anchored-plan.md`, `python/larch/implement/preflight.py`)

## Decision 6: Hard constraints to preserve
- **Question**: What must not break?
- **Resolution**: Panel behavior unchanged; existing batch, manifest, and wire contracts preserved; every committed run carries `difficulty-rating.json` including `--self-review` runs; run-log redaction and json-object sanitizer invariants preserved.
- **Source**: issue + codebase
