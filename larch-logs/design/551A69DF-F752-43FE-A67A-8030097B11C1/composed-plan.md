## Plan

## Scope

Add one static review-panel lane:

- Tool: Cursor.
- Model: `auto`.
- Profile: `agents/reviewer-plan-fidelity.md`, the Plan Correctness/Completeness reviewer.
- Tiers: TRIVIAL, MODERATE, and HARD.
- Surfaces: `/review` and `/implement` Step 5 code-review panel.

Do not change `/design` plan-review reviewers or voter slots.

## Approach

1. Fix `CURSOR_AUTO_MODEL` definition order before extending `review.panel`.
   - Move `CURSOR_AUTO_MODEL: Final = "auto"` (and keep `CURSOR_DEFAULT_MODEL` adjacent if needed) above `ROLE_DEFAULTS` in `config.py` so the new `SlotDefault` can reference `CURSOR_AUTO_MODEL` at import time without `NameError`.
   - Keep the existing constant value and downstream consumers (`report_tokens_cost`, tests) unchanged; this is a definition-order fix only.

2. Add per-slot Cursor model override plumbing end-to-end.
   - Extend `SlotDefault` and waterfall `Slot` parsing with optional `cursor_model`.
   - Validate as a non-empty string without POSIX control characters when present; reject `cursor_model` on Codex rows.
   - In `review_dispatch_panel._append_static_specialist_rows`, copy non-empty `slot.cursor_model` into each Cursor manifest row and set explicit `resolved_model="auto"` on the `plan-fidelity-auto` row so `_with_attribution` does not derive `composer-2.5` from `resolve_model_args` / `LARCH_CURSOR_MODEL`.
   - In `agent_waterfall._launch_slot`, append `--cursor-model <value>` for Cursor slots that carry a non-empty override.
   - In `agent launch-review`, add `--cursor-model`; when present on Cursor launches, use it for the `--model` argv instead of `resolve_model_args("cursor", ...)`, while keeping existing validation and postprocess metadata recording.
   - Persist the resolved override in retry metadata as `OUTER_LAUNCHER_CURSOR_MODEL` via `_review_append_outer_meta` (including preflight paths) and replay it from `collect_results._launch_outer_retry` with `--cursor-model`.
   - Keep Codex `model_role` behavior unchanged.

3. Add specialist prompt wiring for plan-fidelity context.
   - In `rendering._specialist_payload_bytes` and `rendering._render_specialist_text`, add a separate `include_context` rule: when `agent_base == "reviewer-plan-fidelity"` and (`args.plan_file` or `args.feature_file`) is present, set `include_context` true regardless of `args.mode` or `diff_mode`.
   - Keep the existing `reviewer-testing` rule and the `diff` + `generic` fallback unchanged.
   - This ensures docs-only, test-only, and generated-only diffs still embed `<implementation_plan>` / `<feature_description>` for plan-fidelity review.

4. Add the Cursor/auto plan-fidelity static slot.
   - Register `plan-fidelity-auto` in `review.panel` with `cursor_model=CURSOR_AUTO_MODEL` (now defined above `ROLE_DEFAULTS`).
   - Use `agents/reviewer-plan-fidelity.md` and output basename `cursor-specialist-plan-fidelity-auto-output.txt`.
   - Emit from `_append_static_specialist_rows` whenever Cursor is available.
   - Special-case TRIVIAL: keep existing Codex-only singleton specialists, but do not filter out the additive `plan-fidelity-auto` Cursor row when both vendors are available.

5. Keep existing panel behavior stable.
   - Preserve Codex-first TRIVIAL specialist selection for correctness, edge-cases, and testing.
   - Preserve MODERATE/HARD paired Cursor composer-2.5 plus Codex specialist rows.
   - Preserve `--no-fallback`, pruning, degraded retry, collector, tally, and voter behavior.

6. Update attribution, coverage, and telemetry.
   - Map `plan-fidelity-auto` to the same focus area as `plan-fidelity` in `review_tally._static_focus_area`.
   - Static coverage already derives slugs from manifest output basenames via `_static_slug_for_file`; no `STATIC_REVIEWERS` tuple change required.
   - Add timing allowlist entries for `cursor-phase1-plan-fidelity-auto`, `cursor-phase2-plan-fidelity-auto`, and `cursor-specialist-plan-fidelity-auto`.

7. Update public docs and generated topology text.

## Files to modify/create

### UPDATED: python/larch/core/config.py

Move `CURSOR_AUTO_MODEL: Final = "auto"` above `ROLE_DEFAULTS` so `review.panel` slot defaults can reference it at module import. Keep `CURSOR_DEFAULT_MODEL` nearby for readability.

Add optional `cursor_model: str = ""` to `SlotDefault`.

Add a new `review.panel` `SlotDefault`:

- `slot="plan-fidelity-auto"`
- `tool="cursor"`
- `agent="agents/reviewer-plan-fidelity.md"`
- `output="cursor-specialist-plan-fidelity-auto-output.txt"`
- `archetype="plan-fidelity-auto"`
- `focus_area="architecture"` (same bucket as existing plan-fidelity tally mapping)
- `cursor_model=CURSOR_AUTO_MODEL`

Update `doc_fallback` for `review.panel` to mention the additive Cursor/auto plan-fidelity lane.

### UPDATED: python/larch/rendering/rendering.py

In `_specialist_payload_bytes` and `_render_specialist_text`, extend `include_context` with a dedicated plan-fidelity branch:

- `(agent_base == "reviewer-plan-fidelity" and (args.plan_file or args.feature_file))`

This branch must apply for all modes and diff modes (`generic`, `docs-only`, `test-only`, `generated-only`).

Keep the existing `reviewer-testing` rule and `diff` + `generic` fallback unchanged.

### UPDATED: python/tests/rendering/test_rendering.py

Add focused tests that rendering `reviewer-plan-fidelity` with present `plan_file` / `feature_file` includes `<implementation_plan>` and `<feature_description>` blocks and counts their bytes in the payload sidecar for:

- `mode="description"`
- `mode="diff"` with `diff_mode="generic"`
- `mode="diff"` with `diff_mode="docs-only"` (new case from review finding)

### UPDATED: python/larch/agents/agent_waterfall.py

Add `cursor_model: str = ""` to `Slot`.

Extend `_parse_slot_row` to parse optional `cursor_model` with the same string/blank/control-character validation used elsewhere; reject non-empty `cursor_model` when `tool != "cursor"`.

In `_launch_slot`, when `tool == "cursor"` and `slot.cursor_model` is non-empty, append `--cursor-model` with that value.

### UPDATED: python/larch/agents/_review_launcher.py

Add `--cursor-model` to `_review_parser`.

In `_review_validate_args`, reject blank or control-character `--cursor-model` values.

In `_review_launch_cursor`, when `--cursor-model` is present, build `model_args` as `["--model", args.cursor_model]`; otherwise keep `resolve_model_args("cursor", with_effort=True)`.

Extend `_review_append_outer_meta` with optional `cursor_model`; when non-empty, write `OUTER_LAUNCHER_CURSOR_MODEL=<value>`.

Thread `cursor_model=getattr(args, "cursor_model", "")` through all `_review_append_outer_meta` call sites on Cursor launch and preflight paths so retries preserve the override.

### UPDATED: python/larch/agents/collect_results.py

Add `outer_launcher_cursor_model: str = ""` to `RetryMeta`.

Parse `OUTER_LAUNCHER_CURSOR_MODEL` in `_parse_meta`.

In `_launch_outer_retry` for `launcher_kind == "review"` and `meta.tool == "cursor"`, forward `--cursor-model` when `meta.outer_launcher_cursor_model` is non-empty and passes the same blank/control-character validation.

### UPDATED: python/larch/review/review_dispatch_panel.py

In `_append_static_specialist_rows`:

- Special-case TRIVIAL so slot `plan-fidelity-auto` with `tool="cursor"` is emitted even when Codex is available.
- For each Cursor row, include `cursor_model` in the manifest dict when `slot.cursor_model` is non-empty.
- For `plan-fidelity-auto`, set explicit `resolved_model="auto"` in the row before `_append_manifest_row`.
- Keep `STATIC_SLOT_COUNT`, `SLOT_COUNT`, and launch diagnostics accurate.

### UPDATED: python/larch/review/review_tally.py

Add `"plan-fidelity-auto": "architecture"` to `_static_focus_area` (or equivalent alias stripping) so scoreboard and classification do not fall back to generic code-quality.

### UPDATED: python/larch/report/timing.py

Add timing task-kind allowlist entries:

- `cursor-phase1-plan-fidelity-auto`
- `cursor-phase2-plan-fidelity-auto`
- `cursor-specialist-plan-fidelity-auto`

### UPDATED: python/tests/core/test_external_role_defaults.py

Update review panel metadata tests:

- expected static slot count and set include `plan-fidelity-auto`
- new Cursor/auto slot fields
- `cursor_model == CURSOR_AUTO_MODEL`
- docs row text expectations if pinned

Add or adjust a config import smoke assertion that `ROLE_DEFAULTS["review.panel"]` loads without error after the constant move.

### UPDATED: python/tests/review/test_review_pipeline.py

Update panel dispatch tests:

- TRIVIAL includes the additive Cursor/auto plan-fidelity lane when Cursor is available
- MODERATE/HARD include existing pairs plus the additive lane
- Codex-unavailable Cursor panel includes the additive lane
- `STATIC_SLOT_COUNT`, `SLOT_COUNT`, and manifest assertions match the new shape
- Assert the new row has `tool="cursor"`, `cursor_model="auto"`, and `resolved_model="auto"`

Add a focused test that waterfall argv receives `--cursor-model auto` for the new slot.

### UPDATED: python/tests/agents/test_external_dispatch.py

Add or update `agent dispatch-waterfall` slot parsing tests:

- accepts `cursor_model` on Cursor rows
- rejects blank or control-character `cursor_model`
- rejects `cursor_model` on Codex rows
- passes `--cursor-model` through to `agent launch-review`

### UPDATED: python/tests/agents/test_launch_review.py

Add launcher tests for explicit `--cursor-model auto`:

- Cursor `--model` argv uses the override
- postprocess metadata records `model=auto`
- `_review_append_outer_meta` writes `OUTER_LAUNCHER_CURSOR_MODEL=auto`

### UPDATED: python/tests/agents/test_collect_results.py

Add a focused retry test that meta carrying `OUTER_LAUNCHER_CURSOR_MODEL=auto` causes `_launch_outer_retry` to include `--cursor-model auto` on Cursor review retries.

### UPDATED: README.md

Update the `/implement` feature summary for Step 5 reviewer shape. Mention the additive Cursor/auto plan-fidelity reviewer.

### UPDATED: docs/skills.md

Update the `/implement` Step 5 panel description to include the additive Cursor/auto plan-fidelity lane for all tiers.

### UPDATED: docs/review-agents.md

Update active reviewer panel docs:

- mark `reviewer-plan-fidelity` as active through the Cursor/auto lane
- update Note A for `/implement` Step 5
- clarify the lane is additive and does not replace Cursor composer-2.5 specialists

### UPDATED: skills/shared/topology.tsv

Update the `implement.review_and_fix.panel_hard` row to mention the additive Cursor/auto plan-fidelity lane.

### UPDATED: docs/topology.md

Regenerate from `skills/shared/topology.tsv` with `python3 python/cli.py generate topology-docs`.

### MAY_UPDATE: docs/configuration-and-permissions.md

Clarify that `LARCH_CURSOR_MODEL` still controls ordinary Cursor lanes, while the explicit Cursor/auto reviewer lane pins `auto` via per-slot `cursor_model` and launcher `--cursor-model`. Document the operator-visible override only if the implementation exposes `--cursor-model` beyond internal dispatch.

## Edge cases

- Cursor unavailable: drop the new lane like other Cursor rows under `--no-fallback`.
- Codex unavailable: still launch existing Cursor rows plus the Cursor/auto plan-fidelity lane.
- TRIVIAL with both vendors available: keep existing Codex singleton specialists and add only this Cursor/auto lane.
- Operator sets `LARCH_CURSOR_MODEL`: ordinary Cursor rows follow it; `plan-fidelity-auto` still uses `auto` via per-slot override and retry metadata replay.
- Description-mode review with plan/feature files: plan-fidelity reviewer receives embedded plan context.
- Docs-only, test-only, or generated-only diffs with a readable plan file: plan-fidelity reviewer still receives embedded plan/feature context via the dedicated `include_context` rule.
- Round 2 pruning and degraded retry: new output basename participates in the same prune ledger and relaunch matching; retry preserves `OUTER_LAUNCHER_CURSOR_MODEL`.
- Timing: unknown task-kind warnings should not appear for the new lane.

## Failure modes

- Referencing `CURSOR_AUTO_MODEL` inside `ROLE_DEFAULTS` before the constant is defined would raise at import and block `/review` and `/implement`. Mitigate by moving `CURSOR_AUTO_MODEL` above `ROLE_DEFAULTS` and adding a config import smoke test.
- A global env override could accidentally make the new lane run composer-2.5. Mitigate with manifest `cursor_model`, launcher `--cursor-model`, explicit `resolved_model="auto"`, and retry metadata replay.
- Missing plan embed on description or non-generic diff paths would make plan-fidelity review misfire. Mitigate with the dedicated plan-fidelity `include_context` rule (mode/diff-mode independent) and rendering tests including `docs-only`.
- Static coverage or tally could mislabel the new slug. Mitigate with explicit `_static_focus_area` mapping and dispatch/tally tests.
- Retry replay without `OUTER_LAUNCHER_CURSOR_MODEL` would change cost/A-B telemetry on relaunch. Mitigate with meta persistence and collect_results retry test.
- Docs could still claim TRIVIAL is pure Codex singles. Update public docs in the same change.

## Testing strategy

Run focused tests first:

- `python3 -m pytest python/tests/rendering/test_rendering.py -k 'plan_fidelity or specialist'`
- `python3 -m pytest python/tests/core/test_external_role_defaults.py`
- `python3 -m pytest python/tests/review/test_review_pipeline.py -k 'dispatch_panel or degraded_retry or static'`
- `python3 -m pytest python/tests/agents/test_external_dispatch.py`
- `python3 -m pytest python/tests/agents/test_launch_review.py -k 'cursor or model'`
- `python3 -m pytest python/tests/agents/test_collect_results.py -k 'retry and cursor'`

Then run generation checks:

- `python3 python/cli.py generate topology-docs`
- `python3 python/cli.py generate check`

Finally:

- `python3 python/cli.py checks run-relevant`

## Difficulty

This is MODERATE because it changes workflow reviewer topology, external-agent dispatch, manifest schema, specialist rendering, retry metadata, telemetry labels, and public docs. The change is bounded and has direct test seams.

## Acceptance

Run focused tests first:

- `python3 -m pytest python/tests/rendering/test_rendering.py -k 'plan_fidelity or specialist'`
- `python3 -m pytest python/tests/core/test_external_role_defaults.py`
- `python3 -m pytest python/tests/review/test_review_pipeline.py -k 'dispatch_panel or degraded_retry or static'`
- `python3 -m pytest python/tests/agents/test_external_dispatch.py`
- `python3 -m pytest python/tests/agents/test_launch_review.py -k 'cursor or model'`
- `python3 -m pytest python/tests/agents/test_collect_results.py -k 'retry and cursor'`

Then run generation checks:

- `python3 python/cli.py generate topology-docs`
- `python3 python/cli.py generate check`

Finally:

- `python3 python/cli.py checks run-relevant`

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_lines: 395
