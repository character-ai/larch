## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Approach

Implement the minimum scoped prompt-render change for TRIVIAL-only guidelines omission.

- Keep invariants in every specialist and plan-review prompt.
- Omit the guidelines block only when normalized difficulty is `TRIVIAL`.
- Fail open to inclusion when difficulty is missing or invalid.
- Do not change design drafter, Gate C, voter, or aggregator prompts.
- Keep existing architectural framing text unchanged when guidelines are included.
- Thread difficulty as an explicit `--difficulty` flag. Do not infer it from env.
- Include difficulty in specialist prompt caching and compact Codex prompt sentinel reconstruction.
- Defer `docs-only` / `generated-only` diff-mode guideline gating to a follow-up so non-TRIVIAL specialist output stays byte-identical for all diff modes.

## Files to modify/create

### UPDATED: python/larch/rendering/rendering.py

- Import `larch.calibration.difficulty`.
- Add optional parameter to `_architectural_guidelines_review_section()`:
  - `difficulty_value: str = ""`
- Read invariants unconditionally as today.
- Read guidelines only when `difficulty.normalize_tier(difficulty_value) != difficulty.TRIVIAL`.
- Preserve fail-open behavior:
  - `difficulty_value == ""` includes guidelines.
  - invalid difficulty includes guidelines.
- Add `--difficulty` with default `""` to `_parse_specialist()`.
- Add `--difficulty` with default `""` to `render_plan_review_main()` parser.
- In `render_specialist_main()`:
  - call `_architectural_guidelines_review_section(difficulty_value=args.difficulty)` before prompt assembly.
  - pass the gated section into `_render_specialist_text()`.
  - add a cache key line for the gate input, for example `difficulty=<raw value>`.
  - keep existing `diff_mode=<effective_diff_mode>` in the cache key unchanged.
  - keep `architectural_guidelines_sha=...` derived from the gated section actually rendered.
- In `render_plan_review_main()`:
  - mirror `render_specialist_main()`: call `_architectural_guidelines_review_section(difficulty_value=args.difficulty)` before building `architectural_guidelines_prompt`.
  - build `architectural_guidelines_prompt` from that gated section exactly as today.
- Update payload sidecar accounting in both render paths:
  - in `_specialist_payload_bytes()`, accept the rendered architectural section (or recompute via the same gate) and add `_byte_len(...)` when non-empty.
  - in `render_plan_review_main()`, add `_byte_len(architectural_guidelines_section)` to `payload_bytes` when the section is non-empty.
- Keep non-TRIVIAL rendered prompt text byte-identical. Avoid wording edits.

### UPDATED: python/larch/review/plan_review_panel.py

- Add `--difficulty`, `tier` to every `render plan-review` subprocess call in:
  - `_static_slot_rows()`
  - `_generic_plan_codex_row()`
  - `_dynamic_slot_rows()`
- Remove the unused `_ = tier` in `_dynamic_slot_rows()` once the value is threaded.
- Keep the existing `tier` source and model-role behavior unchanged.

### UPDATED: python/larch/review/review_dispatch_panel.py

- Add `--difficulty`, `tier` to `waterfall_args`.
- In `_synthesize_dynamic_slots()`, append `--difficulty`, `tier` to the `render specialist` `render_args` list (alongside existing `--diff-mode` forwarding when present).
- Do not change panel tier selection, round caps, or model role selection.

### UPDATED: python/larch/agents/agent_waterfall.py

- Add `difficulty: str = ""` to `Options`.
- Accept `--difficulty` in `_parse_args()`; empty is allowed; forward non-empty values unchanged.
- Do not coerce missing or invalid values to `TRIVIAL`.
- Do not add control-character validation for `--difficulty`.
- Include `--difficulty` in `_common_args()` when non-empty so it reaches launchers that accept it.

### UPDATED: python/larch/agents/_review_launcher.py

- Add `--difficulty` with default `""` to `_review_parser()`.
- Forward `--difficulty` from `_review_specialist_render_args()` for both live args and sentinel reconstruction.
- Include `DIFFICULTY=<value>` in compact Codex prompt sentinel sidecars when present and safe for the line-oriented format.
- Rehydrate `DIFFICULTY` from sentinels so prompt reconstruction hashes stay stable for TRIVIAL slim prompts.
- Keep existing sentinel keys and hash behavior backward-compatible for old sidecars without `DIFFICULTY`.

### UPDATED: python/larch/agents/_claude_runner.py

- Add `--difficulty` with default `""` to `launch_claude_review_main()` parser.
- When rendering from `--agent-file`, forward `--difficulty` into the `render specialist` argv.
- Prefer reusing `_review_specialist_render_args()` (build a compatible args/sentinel namespace) so the Claude path stays aligned with `launch-review`.
- Land together with the `agent_waterfall` `_common_args()` change so Claude waterfall slots do not reject unknown flags.

### UPDATED: python/tests/rendering/test_rendering.py

Add focused renderer tests.

- `_architectural_guidelines_review_section()`:
  - TRIVIAL includes the invariants block and omits the guidelines block.
  - MODERATE includes both blocks.
  - missing difficulty includes both blocks.
  - invalid difficulty includes both blocks.
- `render_specialist_main()`:
  - with `--difficulty TRIVIAL`, output has invariants but no guidelines.
  - with `--difficulty MODERATE`, output has both blocks.
  - cache creates different cache files for TRIVIAL and MODERATE, even with identical other inputs.
  - cache does not reuse slim output for a non-TRIVIAL render.
  - TRIVIAL payload sidecar records fewer bytes than MODERATE when guidelines are present on disk.
- `render_plan_review_main()`:
  - with missing difficulty, output has both blocks (fail-open).

Update existing payload sidecar expectations that currently exclude architectural section bytes. When repo architectural files are present during render, expected totals must include the gated section length (or patch fixtures to `absent` for deterministic counts). Affected tests:

- `test_render_specialist_payload_sidecar_counts_inline_diff_context`
- `test_render_plan_fidelity_includes_plan_context_for_all_review_modes`
- `test_render_specialist_payload_sidecar_counts_description_and_cache_hit`
- `test_render_plan_review_payload_sidecar_counts_cursor_plan_and_feature`
- `test_render_plan_review_body_file_payload_sidecar_counts_body_feature_and_plan`

Prefer recomputing expected totals via the same gate helper used in production rather than hard-coding stale literals.

### UPDATED: python/tests/review/test_review_pipeline.py

Extend existing `_synthesize_dynamic_slots` render-call assertions.

- Assert `render specialist` argv includes `--difficulty` with the normalized `tier` passed into `_synthesize_dynamic_slots()`.
- Add a focused case for `tier="TRIVIAL"` so dynamic pre-rendered prompts omit guidelines (invariants present, guidelines absent).

### MAY_UPDATE: python/tests/agents/test_launch_review.py

Add or update tests only where compact specialist sentinel reconstruction is already covered.

- Cover `DIFFICULTY` in `_review_specialist_render_args(..., sentinel=...)`.
- Cover that missing `DIFFICULTY` still reconstructs with fail-open defaults.

### MAY_UPDATE: python/tests/agents/test_agent_waterfall.py

Add or update tests only if existing parser coverage for `dispatch-waterfall` argv is present.

- Cover that `--difficulty TRIVIAL` parses into `Options`.
- Cover that `_common_args()` forwards it.

## Edge cases

- Empty or invalid difficulty must include guidelines.
- Old compact prompt sentinel files without `DIFFICULTY` must still reconstruct.
- Specialist renders with no `--difficulty` must include guidelines unless normalized tier is TRIVIAL.
- Plan-review renders with `--difficulty TRIVIAL` must omit guidelines; missing `--difficulty` must fail open to full inclusion.
- Dynamic scout pre-renders in `_synthesize_dynamic_slots()` must receive the same tier as waterfall dispatch.
- Plan-review static, generic, and dynamic slots must all receive the same tier.
- Cache keys must differ for slim and full prompt states.
- `launch-claude-review` and `launch-review` must accept forwarded `--difficulty` before waterfall starts passing it.
- Payload sidecar tests must account for architectural bytes once telemetry is corrected.

## Failure modes

- If difficulty is not threaded through `_synthesize_dynamic_slots()`, TRIVIAL dynamic Cursor slots still receive full guidelines baked into `prompt_file`.
- If difficulty is not added to `launch-claude-review`, waterfall forwarding breaks Claude slots or leaves them on full prompts.
- If difficulty is not threaded through one other dispatch path, TRIVIAL reviewers still receive the full guidelines payload.
- If `render_plan_review_main()` does not pass `args.difficulty` into `_architectural_guidelines_review_section()`, TRIVIAL plan-review prompts still include the full guidelines block.
- If difficulty is omitted from the specialist cache key, slim and full prompts can cross-contaminate.
- If compact sentinel reconstruction omits difficulty, Codex prompt sidecar hash checks can fail or reconstruct the wrong prompt.
- If invalid difficulty defaults to TRIVIAL, guidelines can be incorrectly suppressed.
- If plan-review payload telemetry omits architectural bytes, TRIVIAL savings are underreported.
- If existing payload sidecar tests are not updated alongside telemetry fixes, CI fails on unchanged byte-total assertions.

## Testing strategy

Run focused tests first.

- `python3 -m pytest python/tests/rendering/test_rendering.py -k "architectural or render_specialist_cache or render_plan_review or payload_sidecar"`
- `python3 -m pytest python/tests/review/test_review_pipeline.py -k "synthesize_dynamic_slots and difficulty"`
- If agent parser or sentinel tests are changed, run those specific test files.
- Run changed-file Python lint/type checks per repo practice, for example ruff/pyright on the changed Python files or the nearest existing `make py-lint` target if no narrower project target exists.

difficulty: MODERATE
diff_lines: 255
