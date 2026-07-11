### FINDING_1: Static Cursor rows can omit resolved_model
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Removing `cursor_model` overrides can leave static Cursor dispatch rows without `resolved_model`, even though launches default to Composer 2.5. This violates the requirement that every Cursor lane manifest records `resolved_model=composer-2.5`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In review_dispatch_panel.py _append_static_specialist_rows add an elif slot.tool == "cursor" branch that sets resolved_model via _resolved_model_for_row("cursor") when slot.cursor_model is empty; omit cursor_model unless an explicit override is present


### FINDING_2: Review-pipeline tests still assert Cursor auto
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Cost Schema Compatibility
- **Severity**: major
- **Concern**: `python/tests/review/test_review_pipeline.py` contains static, dynamic, and plan-review manifest assertions that still expect `cursor_model` or `resolved_model` to equal `"auto"`. The file is absent from the proposed plan and focused pytest commands, so the runtime change can leave `make py-test` failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/tests/review/test_review_pipeline.py with expectations for composer-2.5 default resolution and include python3 -m pytest python/tests/review/test_review_pipeline.py in Testing strategy
  - From Codex-Arch: Add `python/tests/review/test_review_pipeline.py` to the plan and update these assertions to Composer 2.5 or standard-resolution expectations while preserving panel-shape and role checks
  - From Cursor-Innovation: Add ### UPDATED: python/tests/review/test_review_pipeline.py; update static, dynamic, and TRIVIAL dispatch assertions to composer-2.5 default resolution (empty cursor_model when unset); include the file in Testing strategy step 1
  - From Cursor-Pragmatic: Add ### UPDATED: python/tests/review/test_review_pipeline.py expecting resolved_model composer-2.5 (and no forced cursor_model unless overridden); add python3 -m pytest python/tests/review/test_review_pipeline.py to Testing strategy step 1
  - From Cursor-Requirements: Add ### UPDATED: python/tests/review/test_review_pipeline.py to the plan; update manifest expectations to composer-2.5 default resolution and neutral override sentinels where override plumbing is tested
  - From Cursor-dyn-Cost Schema Compatibility: Add ### UPDATED: python/tests/review/test_review_pipeline.py; expect composer-2.5 (or absent cursor_model with resolved_model from the standard chain) and include the file in the focused pytest command.


### FINDING_3: Installation documentation still describes per-slot Cursor auto
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Cost Schema Compatibility
- **Severity**: major
- **Concern**: `docs/installation-and-setup.md` still documents reviewer-panel rows using per-slot `auto`, and is absent from the planned documentation updates. Existing acceptance patterns may not catch backtick-wrapped or otherwise non-adjacent Cursor/auto wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: docs/installation-and-setup.md replacing per-slot auto with Composer 2.5 default-resolution wording consistent with docs/external-reviewers.md
  - From Codex-Arch: Add `docs/installation-and-setup.md` to the plan and replace the reviewer-panel `auto` references and model example with Composer 2.5/default-resolution wording
  - From Cursor-Innovation: Add ### UPDATED: docs/installation-and-setup.md replacing per-slot auto with Composer 2.5 default resolution; extend acceptance greps to catch backtick-wrapped auto in docs and skills
  - From Cursor-Pragmatic: Add ### UPDATED: docs/installation-and-setup.md replacing per-slot `auto` with Composer 2.5 default-resolution wording consistent with other doc updates
  - From Cursor-Requirements: Add ### UPDATED: docs/installation-and-setup.md; replace per-slot auto with Composer 2.5 default resolution and optional per-slot cursor_model override wording consistent with docs/configuration-and-permissions.md
  - From Cursor-dyn-Cost Schema Compatibility: Add ### UPDATED: docs/installation-and-setup.md replacing per-slot auto with Composer 2.5 default resolution; include it in the final doc sweep.


### FINDING_4: Configuration documentation update is too narrow
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-Cost Schema Compatibility
- **Severity**: major
- **Concern**: The planned changes to `docs/configuration-and-permissions.md` focus too narrowly on CI-recovery or fixer prose. The file also documents `auto` as a valid `LARCH_CURSOR_MODEL` example and describes reviewer-panel per-slot Cursor auto, leaving stale operator guidance after implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Tighten acceptance step 4: add patterns for per-slot `auto`, Cursor `auto`, and LARCH_CURSOR_AUTO_; grep docs/configuration-and-permissions.md and docs/installation-and-setup.md explicitly; state configuration-and-permissions must drop reviewer-pin and LARCH_CURSOR_MODEL auto example lines, not only CI-recovery prose
  - From Cursor-Pragmatic: Broaden the ### UPDATED: docs/configuration-and-permissions.md bullets to explicitly replace the LARCH_CURSOR_MODEL example and reviewer-panel per-slot auto bullets, not only CI-recovery fixer text
  - From Codex-Pragmatic: Add this line to the documentation update and extend the acceptance sweep to catch Cursor-context references where `Cursor` and `auto` are not adjacent
  - From Cursor-dyn-Cost Schema Compatibility: Expand the docs/configuration-and-permissions.md bullets to update the LARCH_CURSOR_MODEL example and the reviewer-panel pinning paragraph, not only CI-recovery routing.


### FINDING_5: Acceptance grep for `"auto"` is overbroad and incomplete
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: major
- **Concern**: The proposed final sweep neither catches all Cursor-context documentation and environment-variable references nor safely distinguishes Cursor model uses from unrelated `"auto"` literals in `python/larch/`. As written, it can miss stale documentation or fail on unrelated categories and dialectic values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Tighten acceptance step 4: add patterns for per-slot `auto`, Cursor `auto`, and LARCH_CURSOR_AUTO_; grep docs/configuration-and-permissions.md and docs/installation-and-setup.md explicitly; state configuration-and-permissions must drop reviewer-pin and LARCH_CURSOR_MODEL auto example lines, not only CI-recovery prose
  - From Cursor-Pragmatic: Narrow the acceptance check to Cursor-model surfaces (for example CURSOR_AUTO_MODEL, cursor_model auto producers, or an allowlisted rg) and document the dialectic/categories carve-out already noted in Edge cases
  - From Codex-Pragmatic: Add this line to the documentation update and extend the acceptance sweep to catch Cursor-context references where `Cursor` and `auto` are not adjacent


### FINDING_7: Cursor cost schema still requires the removed auto lane
- **Reviewer(s)**: Cursor-dyn-Cost Schema Compatibility
- **Severity**: major
- **Concern**: After removing auto cost emission, detailed pricing still requires `CURSOR_AUTO_COST` alongside Composer and Grok costs. Fresh reports can therefore fall back to aggregate-only output even when Composer and Grok buckets are present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Cost Schema Compatibility: In report_tokens_cost.py, switch has_cursor_components, _emit_cost_line(), and render_cost_line_from_args() to a two-lane Composer/Grok contract only; drop cursor_auto_cost assignment in price_run().


### FINDING_8: Launch-review tests retain auto override fixtures
- **Reviewer(s)**: Codex-Requirements, Cursor-dyn-Cost Schema Compatibility
- **Severity**: major
- **Concern**: `python/tests/agents/test_launch_review.py` is omitted from the plan even though its fixtures explicitly pass `--cursor-model auto` and assert `MODEL=auto` metadata. The suite may fail after the model change, and the fixtures preserve a forbidden Cursor/auto example.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: add `python/tests/review/test_review_pipeline.py` and `python/tests/agents/test_launch_review.py` as updated files; assert default Composer 2.5 resolution in pipeline tests, replace generic override fixtures with a non-auto sentinel, and include both files in focused testing
  - From Cursor-dyn-Cost Schema Compatibility: Add ### UPDATED: python/tests/agents/test_launch_review.py; keep override-plumbing coverage with a neutral sentinel model (not "auto") per the plan test guidance.


