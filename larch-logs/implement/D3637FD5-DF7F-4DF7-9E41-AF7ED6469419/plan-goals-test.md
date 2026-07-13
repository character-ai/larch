## Goal
Implement issue #7114: [IMPLEMENTING] contract-unification [FEATURE] Shared panel/voter dispatch layer.

## Implementation Plan
## Plan

## Approach

Create one shared review-dispatch module for state, topology lookup, model attribution, calibration snapshots, parse-rate validation, and final voter KV emission. Keep each dispatcher responsible for prompts, availability, retry policy, launch mechanics, and family-specific path placeholders.

Preserve code-review’s absent voter paths as `None` until a wire boundary; never construct `Path("")`. Preserve plan-review’s existing concrete tmpdir placeholder paths for skipped or failed slots.

Make final voter emission in-process and contract-stream safe. Reuse a pure ordered voter-status row builder, emit every row through `logging_util.emit_kv`, then emit `DISPATCH_OK`. Parameterize row layout independently from paths-file policy: code review retains its sequential per-voter order, while plan review retains its interleaved order. Do not add a `voter-status-block` subprocess or require fake-harness support for one.

### NEW: python/larch/review/dispatch_shared.py

- Add the canonical mutable `DispatchState`, with voter paths typed `Path | None`, current status defaults, and an explicit helper that serializes `None` as `""` only at CLI, paths-file, done-sidecar, and KV boundaries.
- Add the shared prompt-result value type used by both voter dispatchers without changing their prompt-file wire contracts.
- Add topology-keyed slot and voter-policy builders over `external_defaults.slot_defaults()` and `external_defaults.voter_policies()`. Keep prompt rendering and family-specific row assembly local.
- Add the sole `_resolved_model_for_row(tool, model_role, default_model)` definition. Normalize unsupported roles to `default`, preserve explicit defaults, and return `unknown` on resolver errors.
- Add shared manifest-attribution helpers that accept caller-supplied model role and default model, preserving vendor, role, and resolved-model fields.
- Add a calibration snapshot helper with injected runner, work directory, and family-specific design/review log-root inputs. Preserve feedback opt-out, same-directory temporary files, atomic replacement, cleanup, and `None` on failure.
- Add parse-rate result validation over a caller-built argv and injected runner. Accept only `OK` or `NOT_SUBSTANTIVE` from the final non-empty output line; fail closed otherwise.
- Add a pure ordered voter-status row builder and shared final-KV emitter with explicit row-layout policies: `code_review_sequential` and `plan_review_interleaved`. Emit rows through `logging_util.emit_kv`, then emit `DISPATCH_OK`.
- Support explicit paths-file policies independently of row layout: `always` for code review and `nonempty` for plan review. Preserve code review’s existing paths-file position and 14-line contract, plus plan review’s existing omission when the file is empty or absent.
- Keep all filesystem, logging, and runner seams injectable for focused tests.

### UPDATED: python/larch/review/voting.py

- Extract the ordered, pure voter-status row builder currently embodied by `voter_status_block_main`.
- Keep `voter_status_block_main`’s existing CLI behavior, plan-review interleaved layout, and nonempty paths-file gate by calling the shared builder with `plan_review_interleaved`.
- Let the shared emitter call the builder in-process, avoiding a subprocess failure path that could omit voter KVs while still emitting `DISPATCH_OK`.

### UPDATED: python/larch/agents/agent_voters.py

- Replace local `DispatchState`, prompt-result type, calibration snapshot, model resolver, parse-rate validation, final emitter, and duplicated voter-policy lookup with shared imports or thin compatibility aliases.
- Load policies through the shared topology-keyed builder using `review.voters`.
- Resolve code-review Codex models with `model_role="vote"` and the existing difficulty-specific default model.
- Keep `_state_from_bindings` family-local. Represent skipped or failed code-review bindings as `None`, not `Path("")`, so their `VOTER_*_PATH` values remain empty.
- Convert concrete paths with the shared serializer only at manifests, subprocess arguments, done-sidecar checks, paths-file writes, and KV emission. Skip absent paths in checks and paths-file writes.
- Route calibration and parse-rate calls through shared helpers with the existing `proc.run` seam and code-review argv.
- Route final output through the shared in-process emitter with `code_review_sequential` layout and the `always` paths-file policy. Preserve degraded-panel calculation, warnings, dispatch success rules, code-review’s unconditional `VOTER_PATHS_FILE`, and the exact existing final KV order.
- Retain module-level names used by existing focused tests for monkeypatching.

### UPDATED: python/larch/review/review_dispatch_panel.py

- Remove the local `_resolved_model_for_row`.
- Use shared topology-keyed slot lookup and manifest-attribution helpers with `review.panel`.
- Preserve trivial-tier filtering, tool availability checks, configured Cursor models, generic-reviewer scheduling, dynamic scout rendering, output paths, weights, focus areas, prompts, and agent-file construction.
- Keep caller-selected model roles and defaults explicit when attributing rows.

### UPDATED: python/larch/review/plan_review_panel.py

- Replace local `DispatchState`, prompt-result type, model resolver, final emitter, and duplicated topology or manifest attribution with shared equivalents.
- Initialize contract-stream routing in `dispatch_voters_main` with `logging_util.quiet_init(argv0="plan-review voter-dispatch")` before final KV emission.
- Keep static, generic, and dynamic rendering orchestration local. Use shared topology and attribution helpers with `design.plan_review_panel`, while continuing to compute Codex roles through `difficulty.codex_review_model_role_for_archetype()` and `difficulty.codex_review_model_role()` before attribution.
- Use the shared voter-policy builder and manifest-row helpers with `design.plan_voters`.
- Keep `_state_from_bindings` family-local and retain its concrete plan tmpdir output paths for skipped or failed voters.
- Retain thin module-level `_fresh_calibration_stats_file(design=...)` and `_parse_rate_retry(design=..., ballot=..., ...)` facades with their current signatures. Have them construct plan-specific inputs and delegate to shared helpers through the existing `larch_proc` and `subprocess` seams.
- Route the 14 final voter KVs through the shared in-process emitter with `plan_review_interleaved` layout and the `nonempty` paths-file policy.
- Route trailing `VOTER_1_RETRIED` and `DEGRADED_PANEL` through `logging_util.emit_kv` as well, preserving their existing post-`DISPATCH_OK` order and contract-stream visibility.
- Preserve plan-specific prompt rendering, scope anchors, payload accounting, dynamic-render warnings, pruning, Claude-only retry behavior, waterfall timeouts, effective-judge rules, and `VOTER_1_RETRIED`.

### NEW: python/tests/review/test_dispatch_shared.py

- Test model resolution for Cursor, each accepted Codex role, difficulty defaults, invalid roles, and resolver failures.
- Test topology-keyed panel and voter builders preserve configured slot metadata.
- Test `DispatchState` accepts concrete `Path` values and preserves absent code-review paths as `None`.
- Test the path serializer emits `""` for absent paths and never turns skipped or failed paths into `"."`.
- Test calibration opt-out, successful atomic replacement, design and review log-root forwarding, failed snapshots, empty snapshots, and temporary-file cleanup.
- Test parse-rate validation for valid, diagnostic-prefixed, empty, unknown, and nonzero results.
- Test final emission through `logging_util` rather than `print()`, including quiet contract-stream capture, exact code-review sequential and plan-review interleaved key orders, paths-file placement or omission, and `DISPATCH_OK` placement.
- Test plan-review trailing `VOTER_1_RETRIED` and `DEGRADED_PANEL` are emitted through the quiet contract stream after `DISPATCH_OK`.
- Add regressions for code-review skipped and failed empty voter paths, plan-review concrete placeholder paths, role-based plan Codex attribution, and the absence of a final-emitter subprocess dependency.

## Edge cases

- A code-review voter may be absent, skipped, failed, or empty; its path remains `None` internally and `""` on the wire.
- A plan-review voter may be skipped or failed; retain its current canonical tmpdir output path.
- A voter paths file may be absent or empty. Code review still emits its paths-file KV in its existing sequential position; plan review retains the nonempty-file gate in its existing interleaved order.
- Tool configuration may omit Codex or Cursor, or use an explicit Cursor model.
- A model role may be missing or invalid. Resolve it as `default`, not `vote`.
- Calibration may be disabled, unable to resolve a log root, fail its subprocess, or produce an empty file.
- Parse-rate retry may return diagnostics before its status. Read the final non-empty line only.
- Dynamic plan-review rendering may fail for one slot. Preserve its per-slot warning and accounting.

## Failure modes

- Treat calibration failure as unavailable feedback, not dispatch failure.
- Treat parse-rate runner failure or malformed output as `NOT_SUBSTANTIVE`.
- Preserve partial-waterfall accounting and per-slot failed or skipped states.
- Do not emit a successful dispatch when no effective judge remains.
- Do not silently change model attribution, absent-path semantics, paths-file policy, either family’s final voter KV order, `DISPATCH_OK` placement, post-dispatch plan-review KVs, or quiet contract-stream routing.
- Keep tally unification, snapshot-family parameterization beyond this helper, and broader dispatch redesign out of scope.

## Testing strategy

Run the new focused shared-module tests:

- `python3 -m pytest python/tests/review/test_dispatch_shared.py`

Run acceptance and touched-module suites:

- `python3 -m pytest python/tests/agents/test_agent_voters.py`
- `python3 -m pytest python/tests/agents/test_external_dispatch.py`
- `python3 -m pytest python/tests/review/test_plan_review_panel.py`
- `python3 -m pytest python/tests/review/test_voting.py`
- `python3 -m pytest python/tests/implement/test_implement_dispatch.py`

Run scoped Python lint for the changed Python files using the repository’s documented scoped lint command. Confirm a net production line reduction and grep for remaining definitions of `_resolved_model_for_row`, `DispatchState`, calibration snapshot, parse-rate validation, and final voter emission.

## Acceptance

Run the new focused shared-module tests:

- `python3 -m pytest python/tests/review/test_dispatch_shared.py`

Run acceptance and touched-module suites:

- `python3 -m pytest python/tests/agents/test_agent_voters.py`
- `python3 -m pytest python/tests/agents/test_external_dispatch.py`
- `python3 -m pytest python/tests/review/test_plan_review_panel.py`
- `python3 -m pytest python/tests/review/test_voting.py`
- `python3 -m pytest python/tests/implement/test_implement_dispatch.py`

Run scoped Python lint for the changed Python files using the repository’s documented scoped lint command. Confirm a net production line reduction and grep for remaining definitions of `_resolved_model_for_row`, `DispatchState`, calibration snapshot, parse-rate validation, and final voter emission.

mechanical_churn: false
diff_lines: 875

## Test plan
(no test plan section in plan-file)
