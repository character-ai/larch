## Proposed Design Outline

### Goals
- Make vendor-fallback reviewer attribution (the `(via <Tool>)` annotation) work for `/review` code-review and `/implement` Step 5 review, not just `/design` plan-review, in the shared final-report Top-reviewers table.
- Generalize the existing `_fallback_label_remap` machinery so one code path serves both surfaces, instead of bolting on a second design-shaped implementation.
- Add regression coverage exercising a code-review manifest with a vendor fallback.

### Non-goals
- No retroactive re-rendering of already-committed historical run-log reports; the fix is forward-looking only.
- No new live in-progress "reviewer-status" display for `/review` — that is a `/design`-only Step 3 UX feature with no code-review analog today.
- No change to voting/point-competition behavior. `code-voter-slots.ndjson` is the voter manifest, not the reviewer/finder manifest this bug concerns; investigation found the reviewer/finder manifest (`panel-manifest.ndjson`) already carries the needed `tool` field for both surfaces.

### Approach sketch
- Generalize `_fallback_label_remap`'s directory-ancestor resolution in `progress_report.py`: it currently assumes `/design`'s two-level `plan-review/round-N` nesting (`round_dir.parent.parent`), which resolves to the wrong directory for code-review's shallower round nesting. Reuse the pattern already established by the working `_collector_env_paths_for_round` helper instead of the hardcoded ancestor jump.
- Derive the nominal (pre-fallback) vendor from the manifest row's own `tool` field rather than reverse-parsing it from the slot-name string, since both `/design` and `/review` manifests already carry `tool` per row. Code-review slot names (e.g. `code-quality`) don't encode tool the way `/design`'s `cursor-plan-arch`/`codex-plan-arch` convention does, so the existing slot-name-prefix table can't recognize them.
- The existing `/design`-only live `reviewer-status.tsv` display (`plan_review_round.write_reviewer_status_tsv`) stays as-is; whatever shared reconciliation logic remains may live in `progress_report.py` or move to a shared module, decided during plan drafting.
- Add a code-review-flavored counterpart to the existing `test_fallback_label_remap_annotates_executing_tool` test.

### Surfaces in scope
- `python/larch/report/progress_report.py` (`_fallback_label_remap`, `_apply_fallback_remap`, ancestor/manifest resolution)
- `python/tests/report/test_progress_report.py` (new regression test)
- `python/larch/review/plan_review_round.py` (only if shared reconciliation logic needs to move here or be exposed differently)

### Open questions
- None.
