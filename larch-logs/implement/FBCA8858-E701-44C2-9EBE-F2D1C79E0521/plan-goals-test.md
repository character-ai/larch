## Goal
Implement issue #6158: [IMPLEMENTING] md-to-py-XII: per-section scaffold/payload instrumentation for generated slot prompts.

## Implementation Plan
## Plan

## Approach

Drafted from direct codebase inspection. `approach-synthesis.txt` is `NO_SKETCHES`, so this plan does not rely on planning-panel agreement.

Add count-only scaffold and payload telemetry without changing prompt text, dispatch behavior, panel topology, voting grammar, or historical log files.

Core rule:

- `prompt_bytes` stays the rendered prompt byte count.
- `payload_bytes` records per-run content the builder knows it inlined or intentionally attaches as prompt payload.
- `scaffold_bytes` is derived as the remaining prompt bytes, with non-negative bounds.
- Missing legacy columns in old TSVs are read as `scaffold_bytes=prompt_bytes` and `payload_bytes=0`.

## Files to modify/create

### UPDATED: python/larch/report/tokens.py

- Extend `_PANEL_PROMPT_SIZE_FIELDS` and `PanelPromptSizeRow` with:
  - `scaffold_bytes`
  - `scaffold_tokens`
  - `payload_bytes`
  - `payload_tokens`
- Add a small parser for non-negative payload byte values from explicit args or `LARCH_PANEL_PAYLOAD_BYTES`.
- Extend `build_panel_dispatch_env()` with optional `payload_bytes`. Always clear any inherited `LARCH_PANEL_PAYLOAD_BYTES` from the base `os.environ` copy before optionally re-setting it, so a prior slot's payload value can never leak into a later fallback or failure dispatch that does not supply its own payload count.
- Extend `append_panel_prompt_size()` with optional `payload_bytes`.
  - Prefer the explicit argument.
  - Fall back to `LARCH_PANEL_PAYLOAD_BYTES`.
  - Default to `0`.
  - Clamp malformed or negative values to `0`.
  - Derive scaffold bytes from prompt bytes and payload bytes without allowing a negative scaffold value.
- Keep telemetry best-effort. Do not let malformed payload metadata fail a dispatch.
- Extend `_PanelCostAggregate` with scaffold and payload totals.
- Update `measure_panel_cost()`:
  - Read new columns when present.
  - Use legacy fallback for old rows.
  - Sort rows by scaffold bytes descending, then stable tie-breakers.
  - Emit scaffold and payload columns in the output TSV while keeping existing realized totals.

### UPDATED: python/larch/rendering/rendering.py

- Add optional `--payload-bytes-output <path>` to:
  - `render specialist`
  - `render voter`
  - `render plan-review`
- Add a helper that writes a decimal byte count plus newline to the sidecar, best-effort only after successful render. Before writing, unlink any existing file at the sidecar path (or write to a fresh unique temp path and atomically replace) so a failed write cannot leave a stale prior render's byte count behind; a reader must see either the current render's count or no file at all, never a stale one.
- Add local payload accounting helpers that count only raw per-run content, not fixed wrapper prose.
- Extend the payload accounting helpers to add ledger-section payload bytes whenever the rendered prompt includes a non-empty ledger section from `_code_ledger_section` or `_plan_ledger_section` — count the bytes of the actual emitted section string (the value those functions return, which already reflects any row-count or byte truncation applied before rendering), never the raw underlying ledger file size; counting the untruncated file would push payload past what was actually rendered and clamp scaffold to zero on oversized ledgers. These sections are generated per run from a findings ledger and are not fixed instruction scaffold, so their bytes must count as payload for both specialist and voter renders (and plan-review renders, when a ledger section is present). Cover a greater-than-12000-byte ledger to pin the truncation case.
- `render plan-review`:
  - Count `feature_file` raw bytes when the feature scope block is inlined.
  - Count `plan_file` raw bytes only for Cursor, where the plan is inlined.
  - Add a `--body-file-payload` boolean. Use it for dynamic scout body files, not for fixed generic role files.
- `render voter`:
  - Count raw scope-anchor bytes only when the anchor is accepted and inlined.
  - Count raw bytes of the non-empty calibration feedback block produced by `_voter_calibration_feedback_block` when calibration stats are enabled — that text is generated per run from live calibration data, not fixed scaffold.
  - Do not count ballot files, because voter prompts path-reference them.
- `render specialist`:
  - Count `description_text` for description-mode prompts.
  - Count raw `feature_file` and `plan_file` bytes only when `_render_specialist_text()` inlines them.
  - Preserve cache behavior. On cache hit, still write the payload sidecar for the cached prompt.
- Keep output prompt text byte-for-byte unchanged except for any unavoidable parser-only flag handling.

### UPDATED: python/larch/review/plan_review_panel.py

- When pre-rendering plan-review prompts, pass `--payload-bytes-output` and read the sidecar.
- Pass `--body-file-payload` for dynamic scout plan-review rows only.
- Extend `_slot_row()` with `payload_bytes` and include it in manifest rows when non-zero.
- For render failure fallback prompts, record `payload_bytes=0`.
- Change `_make_voter_prompt()` to return a small typed result with `prompt_file` and `payload_bytes`, keyed per tool: because `prompt_files` voter rows can choose a different rendered prompt body per tool, a single slot-level `payload_bytes` cannot represent them. Add a `payload_files` map parallel to `prompt_files` on the hand-built voter manifest (including `manifest_lines` alongside `prompt_maps_by_slot`), populated with each tool's own rendered payload count.
- Pass voter payload bytes into:
  - direct Claude voter launch env
  - voter waterfall manifest rows (via the new `payload_files` map)
  - retry launches
- Keep `plan-voter-slots.ndjson` valid for existing `prompt_files` consumers.

### UPDATED: python/larch/review/review_dispatch_panel.py

- In `_synthesize_dynamic_slots()`, pass `--payload-bytes-output` to `render specialist`.
- Read the sidecar and include `payload_bytes` on dynamic `prompt_file` manifest rows.
- Count the dynamic scout's own `rationale` and `prompt_body` bytes (the content `_dynamic_agent_body()` folds into the generated dynamic agent file) as additional payload on top of the sidecar count, since that content is generated per run, not fixed instruction scaffold. Add it directly in `_synthesize_dynamic_slots()` or thread it through an explicit renderer payload input, then include the combined value in each dynamic manifest row's `payload_bytes`.
- Keep static specialist `agent` rows unchanged; their prompt payload is measured by launchers when they render on demand.
- For render fallback to the dynamic agent file body, use `payload_bytes=0` unless a valid sidecar exists.
- Do not change pruning, scout validation, or dynamic slot counts.

### UPDATED: python/larch/agents/agent_waterfall.py

- Extend `Slot` with `payload_bytes: int = 0` and an optional `payload_files: dict[str, int] | None = None` map parallel to `prompt_files`, for rows (such as voter rows) whose payload count differs per launch tool.
- Parse optional manifest `payload_bytes` as a non-negative integer; parse optional `payload_files` the same way `prompt_files` is parsed in `_parse_slot_row`.
- Reject non-integer manifest values unless `--skip-invalid-slots` is active, matching existing invalid-row behavior.
- In `_launch_slot`, when `payload_files` is present, select the active tool's payload count the same way `_prompt_file_for_tool` selects the prompt file; otherwise fall back to the scalar `payload_bytes`.
- Pass the selected payload count through `build_panel_dispatch_env()` when launching a child.
- Ensure fallback phases carry the same payload count as the prompt source they launch.
- Leave prompt selection and vendor fallback order unchanged.

### UPDATED: python/larch/agents/agent_voters.py

- Mirror `plan_review_panel.py`'s voter payload wiring for the code-review voter path used by `/implement` Step 5 and standalone `/review` voters, which currently has no payload sidecar wiring and would otherwise stay at `payload_bytes=0`.
- Pass `--payload-bytes-output` when rendering each voter prompt file (the code-review analog of `_make_voter_prompt`), read the sidecar, and accumulate per-tool counts in the code-review analog of building `prompt_files`.
- Emit a `payload_files` map parallel to `prompt_files` on the hand-built code-review voter waterfall manifest, populated the same way `plan_review_panel.py` populates its voter manifest.
- Thread the selected tool's payload bytes through `build_panel_dispatch_env()` for both direct Claude voter launches and waterfall voter rows.
- Keep ballot construction, voter dispatch order, and retry behavior unchanged.

### UPDATED: python/larch/agents/_review_launcher.py

- When resolving a prompt from `--prompt-file`, use `LARCH_PANEL_PAYLOAD_BYTES` for telemetry.
- When rendering from `--agent-file`, call `render specialist` with a payload sidecar, read it, and pass that value to `append_panel_prompt_size()`.
- Update helper return types as needed so prompt text and payload bytes travel together.
- Keep Codex compact sentinel reconstruction behavior unchanged; if payload metadata is unavailable there, use `0`.

### UPDATED: python/larch/agents/_claude_runner.py

- Mirror `_review_launcher.py` for Claude reviewer launches.
- For prompt-file launches, read payload bytes from `LARCH_PANEL_PAYLOAD_BYTES`.
- For agent-file launches, render specialist with a payload sidecar and pass the count to `append_panel_prompt_size()`.
- Keep Claude voter role, model resolution, and read-tools grants unchanged.

### UPDATED: python/larch/review/review_aggregate.py

- Compute aggregator payload bytes from:
  - raw reviewer findings text inlined into the prompt
  - raw scope-anchor bytes when the scope anchor is accepted and inlined
  - validator feedback bytes on retry attempts, if included in the retry prompt
  - the generated per-run required-reviewer-slot inventory section (`_required_reviewer_slots_prompt_parts`) folded into the prompt — it is per-run variable content, not fixed scaffold
- Include `payload_bytes` in the aggregator slot manifest.
- Inside the retry loop, after composing the updated `prompt_file` text for each attempt (validator feedback changes the prompt body), recompute payload bytes, rewrite the one-row slot manifest (`aggregator-slots.ndjson`), and rebuild `panel_env` with the fresh `payload_bytes` before each dispatch — do not build `panel_env` once outside the loop and reuse it across attempts, or later retries will report stale payload bytes.
- Preserve the current dispatch, validation, retry, warning, and merge behavior.

### UPDATED: python/larch/review/coder_runner.py

- Compute implementer payload bytes from the scrubbed accepted-findings file, per the approved outline.
- Pass that value into `append_panel_prompt_size()`.
- Keep coder prompt text, tool order, submodule scrub behavior, and snapshots unchanged.

### UPDATED: docs/run-logs.md

- Document the new `panel-prompt-sizes.tsv` columns.
- State that rows remain count-only and never include prompt text.
- Document legacy behavior:
  - old committed rows may lack scaffold and payload columns
  - `measure-panel-cost` treats missing scaffold as the whole prompt and missing payload as zero
- Document that `measure-panel-cost` ranks by scaffold bytes.

### UPDATED: python/tests/report/test_tokens.py

- Update panel prompt-size helper tests for new columns.
- Add tests for:
  - explicit payload bytes
  - payload env fallback
  - malformed payload fallback
  - legacy TSV aggregation fallback
  - scaffold-byte sort order in `measure_panel_cost()`
  - `build_panel_dispatch_env()` clears a pre-existing `LARCH_PANEL_PAYLOAD_BYTES` from the base environment when no payload is supplied
- Ensure prompt text still does not appear in TSV output.

### UPDATED: python/tests/rendering/test_rendering.py

- Add focused tests for `--payload-bytes-output` on:
  - plan-review Cursor plan inline vs Codex plan path-reference
  - plan-review dynamic `--body-file-payload`
  - voter scope-anchor inline
  - specialist plan/feature inline and description text
  - specialist cache hit still writes the payload sidecar
  - a failed sidecar write does not leave a stale prior byte count readable at the same path
  - ledger-section bytes are counted as payload for round-2 specialist and voter renders when a non-empty ledger section is present, using the emitted (possibly truncated) section bytes rather than the raw ledger file size, pinned with a greater-than-12000-byte ledger
  - non-empty calibration feedback block bytes are counted as voter payload when calibration stats are enabled

### UPDATED: python/tests/review/test_plan_review_panel.py

- Update plan-review panel materialization tests to assert new TSV columns.
- Add tests that static and dynamic plan-review rows include payload metadata when their renderer sidecars report it.
- Add voter dispatch tests that payload bytes reach direct Claude voter env and waterfall manifest rows, including a per-tool `payload_files` case where two tools launch from different rendered prompt bodies with different payload counts.

### UPDATED: python/tests/review/test_review_pipeline.py

- Update review dispatch panel tests for dynamic slot `payload_bytes`.
- Add a manifest-row test that dynamic specialist payload metadata survives scout synthesis and dispatch setup.
- Add a test that a dynamic slot's `payload_bytes` includes the scout rationale/prompt_body bytes folded into the generated dynamic agent file, not just the sidecar count.
- Update existing panel prompt-size assertions to include scaffold and payload columns.

### UPDATED: python/tests/agents/test_agent_waterfall.py

- Add parser tests for `payload_bytes` and the new `payload_files` per-tool map.
- Add env threading assertions for `LARCH_PANEL_PAYLOAD_BYTES`, including a case where `_launch_slot` selects the active tool's entry from `payload_files`.
- Update panel prompt-size materialization tests to assert scaffold and payload counts.
- Add invalid-row coverage for malformed `payload_bytes` (and malformed `payload_files` entries) under strict and skip-invalid modes.

### UPDATED: python/tests/agents/test_launch_review.py

- Add tests for prompt-file launches using `LARCH_PANEL_PAYLOAD_BYTES`.
- Add tests for agent-file launches where the renderer payload sidecar is consumed.
- Keep the existing “no panel slot writes no TSV” test valid.

### UPDATED: python/tests/agents/test_agent_voters.py

- Add tests that the code-review voter path (`agent_voters.py`) passes `--payload-bytes-output`, reads the sidecar, and populates a `payload_files` map parallel to `prompt_files`.
- Assert the selected tool's payload bytes reach `build_panel_dispatch_env()` / `LARCH_PANEL_PAYLOAD_BYTES` for both direct Claude voter launches and waterfall voter rows.
- Assert existing ballot construction, dispatch order, and retry behavior are unchanged.

### UPDATED: python/tests/review/test_review_aggregate.py

- Update aggregator TSV tests for new columns.
- Add retry coverage where validator feedback changes the payload count, asserting `panel_env` and the rewritten slot manifest carry the recomputed value on the next attempt rather than the first attempt's value.
- Assert aggregator payload bytes include raw findings, accepted scope-anchor content, and the generated required-reviewer-slot inventory bytes — not fixed scaffold.

### UPDATED: python/tests/review/test_review_and_fix.py

- Add or update review-fix coder telemetry coverage.
- Assert implementer rows include payload bytes derived from the scrubbed accepted-findings file.
- Assert prompt text and findings text still do not leak into `panel-prompt-sizes.tsv`.

## Edge cases

- Old committed `panel-prompt-sizes.tsv` files lack new columns. Aggregation must keep working.
- Payload sidecar writes can fail. Rendering should still succeed; the caller records `0`, and a stale sidecar from an earlier render must never be read as if it were current.
- Render failures that fall back to simple prompts must not reuse stale sidecar values.
- `prompt_files` voter rows can launch with a fallback vendor. The payload count must match the prompt family actually launched, via the per-tool `payload_files` map, not the primary vendor assumption.
- Dynamic plan-review generic fixed role bodies must not be misclassified as payload.
- Payload bytes can be larger than prompt bytes for the implementer path requested by the outline. Keep scaffold non-negative and document the distinction.
- Malformed manifest payload values should fail closed in normal mode and drop under `--skip-invalid-slots`.
- Retry attempts (aggregator) must recompute payload per attempt; a stale `panel_env` built before the loop must not be reused across attempts.
- `build_panel_dispatch_env()` must not let a payload value inherited from a parent process's `os.environ` leak into a child dispatch that supplies no payload of its own.
- Ledger sections can be truncated before rendering; payload accounting must count the emitted section, not the raw ledger file, or scaffold can clamp to zero on oversized ledgers.
- The code-review voter path (`agent_voters.py`) must not silently stay at `payload_bytes=0` while the plan-review voter path is fully wired.

## Failure modes

- If payload metadata is not threaded through one launch path, `scaffold_bytes` will be inflated for that slot kind.
- If sidecar files are stale after a render failure, payload bytes can be wrong.
- If legacy aggregation treats missing scaffold as zero, old logs will dominate rankings incorrectly.
- If manifest validation is too strict, existing dynamic or voter slots may drop.
- If the new renderer flag changes stdout, prompts or caller parsers can break.

## Testing strategy

Run focused tests only for changed files:

- `python3 -m pytest python/tests/report/test_tokens.py`
- `python3 -m pytest python/tests/rendering/test_rendering.py`
- `python3 -m pytest python/tests/review/test_plan_review_panel.py`
- `python3 -m pytest python/tests/review/test_review_pipeline.py`
- `python3 -m pytest python/tests/agents/test_agent_waterfall.py`
- `python3 -m pytest python/tests/agents/test_launch_review.py`
- `python3 -m pytest python/tests/agents/test_agent_voters.py`
- `python3 -m pytest python/tests/review/test_review_aggregate.py`
- `python3 -m pytest python/tests/review/test_review_and_fix.py`

Then run changed-file lint/type checks if the environment has the Python dev tools:

- `make py-lint`
- `make py-test` only if the focused test set exposes shared fixture or import fallout

## Non-goals

- Do not compress prompt prose.
- Do not change reviewer, voter, aggregator, or coder output contracts.
- Do not migrate historical run logs.
- Do not add new run-log artifact batches.

## Acceptance

Run focused tests only for changed files:

- `python3 -m pytest python/tests/report/test_tokens.py`
- `python3 -m pytest python/tests/rendering/test_rendering.py`
- `python3 -m pytest python/tests/review/test_plan_review_panel.py`
- `python3 -m pytest python/tests/review/test_review_pipeline.py`
- `python3 -m pytest python/tests/agents/test_agent_waterfall.py`
- `python3 -m pytest python/tests/agents/test_launch_review.py`
- `python3 -m pytest python/tests/agents/test_agent_voters.py`
- `python3 -m pytest python/tests/review/test_review_aggregate.py`
- `python3 -m pytest python/tests/review/test_review_and_fix.py`

Then run changed-file lint/type checks if the environment has the Python dev tools:

- `make py-lint`
- `make py-test` only if the focused test set exposes shared fixture or import fallout

diff_lines: 950

## Test plan
(no test plan section in plan-file)
