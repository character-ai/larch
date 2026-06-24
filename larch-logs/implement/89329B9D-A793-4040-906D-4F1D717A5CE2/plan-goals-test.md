## Goal
Implement issue #5311: [IMPLEMENTING] Route Codex reviews/votes/fixes to gpt-5.4-mini; keep implementer on 5.5.

## Implementation Plan
## Plan

## Approach

- Add explicit **Codex model roles**: default/strong, review, vote, and fix.
- Keep **Step 2 implementer** and **brainstorm** on `LARCH_CODEX_MODEL`, default `gpt-5.5`.
- Add role env keys:
  - `LARCH_CODEX_REVIEW_MODEL`, default `gpt-5.4-mini`
  - `LARCH_CODEX_VOTE_MODEL`, default `gpt-5.4-mini`
  - `LARCH_CODEX_FIX_MODEL`, default `gpt-5.4-mini`
- Make **review/vote/fix roles ignore `LARCH_CODEX_MODEL`** so a global strong override does not re-upgrade cheap roles.
- **Preserve the existing default-role fallback contract:** for `codex_role="default"`, keep the current `resolve_model_args("codex", default_model=...)` and `agent model-args --default-model` ladder: `LARCH_CODEX_MODEL`, plugin option, then `default_model or CODEX_DEFAULT_MODEL` (`gpt-5.5`). Do not hardcode `gpt-5.5` as the sole terminal default when `default_model` is supplied.
- For **review/vote/fix roles**, resolve only role env keys then role defaults; **ignore** the `default_model` kwarg and `--default-model` CLI flag.
- Keep **Cursor** defaults unchanged at `composer-2.5`.
- Keep **brainstorm** unchanged. Existing brainstorm `agent launch-review --tool codex` calls stay on default (strong) unless the caller passes a cheap role.
- Remove the **round-2+ Codex generic reviewer collapse** in plan review and code review.
- Move **code-review plan-fidelity and pragmatism voters** to Codex primary with Cursor fallback, then Claude only when both external vendors fail.
- Leave **validity voter** on Cursor primary; **never** let validity fall through to Codex when Cursor is absent or fails.
- Make **`--model-role` opt-in at scoped launch sites**. Do **not** infer review/vote roles inside generic `agent dispatch-waterfall` from slot names; decompose and other non-review callers stay on default.
- **Split code-review voter dispatch** so voter-1 (validity) never shares a fallback-enabled waterfall with Codex-primary voters 2–3. Mirror the `plan_review_panel.dispatch_voters` pattern: voter-1 on a Cursor-only path; voters 2–3 on a separate two-slot waterfall with fallback enabled.
- **Voter-1 Cursor launch contract:** use direct `agent launch-review --tool cursor` or a one-slot `agent dispatch-waterfall --no-fallback`. Do **not** pass `--no-fallback` to `agent launch-review`; that flag exists only on `agent dispatch-waterfall`. Direct single-tool launch has no phase-2 fallback, so voter-1 cannot fall through to Codex.
- **Bind waterfall results by manifest slot identity**, not compressed `ALL_OUTPUT_FILES` position. `agent_waterfall.dispatch_waterfall` omits empty `final_outputs` entries from `ALL_OUTPUT_FILES` / `ALL_OUTPUT_TOOLS` (see `python/agent_waterfall.py` around 923–929), so zip index 0 is the first *successful* slot, not manifest row 0. Add a shared resolver that walks each manifest NDJSON row, matches the winning path from `ALL_OUTPUT_FILES_PATH` (and phase-2/phase-3 suffix variants), pairs the parallel compressed tool token for that matched path, and consults `DROPPED_SLOTS_FILE` when a row has no match. Derive semantic `VOTER_*_TOOL` labels from slot policy plus the winning external tool.
- Recompute **`expected_judges`** from the launched slot policy, not `cursor_path` alone.
- Replace **`codex_slots_enabled`** with **`codex_available == "true"`** for static and dynamic Codex specialist gating.
- Preserve **review-panel `--no-fallback` policy**: append only when both vendors are present **and** `round_num < 2` (round-1 dual-vendor behavior unchanged; round 2+ dual-vendor allows cross-vendor fallback).
- Persist and replay **`--model-role` on collector retries** so cheap Codex launches do not revert to strong default after parse/timeout retry.
- Make the **Codex health probe** fail closed on invalid review-model resolution so Step 0 catches blank role env before panel launch.
- Update **`.claude-plugin/plugin.json`** so `codex_model` describes only the strong/default Codex role, not review or voting.

## Files to modify/create

### UPDATED: python/config.py

- Add constants:
  - `ENV_LARCH_CODEX_REVIEW_MODEL`
  - `ENV_LARCH_CODEX_VOTE_MODEL`
  - `ENV_LARCH_CODEX_FIX_MODEL`
- Add default constants if local style supports it:
  - `CODEX_DEFAULT_MODEL = "gpt-5.5"`
  - `CODEX_REVIEW_MODEL_DEFAULT = "gpt-5.4-mini"`
  - `CODEX_VOTE_MODEL_DEFAULT = "gpt-5.4-mini"`
  - `CODEX_FIX_MODEL_DEFAULT = "gpt-5.4-mini"`

### UPDATED: python/agents.py

- Extend `resolve_model_args` with a keyword-only Codex role, for example:
  - `codex_role: Literal["default", "review", "vote", "fix"] = "default"`
- **Keep** the existing `default_model: str = ""` parameter unchanged on the function signature.
- Preserve existing Cursor behavior.
- For Codex `default` role:
  - Resolve `LARCH_CODEX_MODEL`, then plugin option, then `default_model or CODEX_DEFAULT_MODEL` (same contract as today's `default_model or "gpt-5.5"`).
  - Do not bypass `default_model` when env and plugin option are unset.
- For Codex `review` / `vote` / `fix` roles:
  - `review` resolves `LARCH_CODEX_REVIEW_MODEL`, then `CODEX_REVIEW_MODEL_DEFAULT`.
  - `vote` resolves `LARCH_CODEX_VOTE_MODEL`, then `CODEX_VOTE_MODEL_DEFAULT`.
  - `fix` resolves `LARCH_CODEX_FIX_MODEL`, then `CODEX_FIX_MODEL_DEFAULT`.
  - **Ignore** `default_model` on non-default roles.
- Reuse current blank and control-character validation.
- Do not let `LARCH_CODEX_MODEL` override role-specific review/vote/fix defaults.
- Add `agent model-args --codex-role default|review|vote|fix` for testability and script parity.
- **Keep** `agent model-args --default-model`; apply it only when `--codex-role` is `default` (or omitted, since default is the default role).
- Add `agent launch-review --model-role default|review|vote|fix`.
- Use `--model-role default` by default so brainstorm stays strong.
- Do **not** add `--no-fallback` to `agent launch-review` in this change; voter-1 isolation uses direct Cursor launch or a one-slot waterfall.
- In `_review_launch_codex`, pass `codex_role=args.model_role` (do not pass a `default_model` override; default role keeps existing strong resolution).
- In `launch-codex-exec`, add `--model-role default|fix` and pass it to `resolve_model_args`.
- When writing launch `.meta`, persist `OUTER_LAUNCHER_MODEL_ROLE=<role>` for `agent launch-review` and `agent launch-codex-exec` launches that use a non-default role (and for explicit `default` when tests need parity).
- Fix `_run_one_codex_probe`: resolve with `codex_role="review"`; on `ValueError`, write the error to the probe sidecar and return a non-retry probe failure instead of continuing with `model_args=[]`.
- Leave `launch-codex-implement`, Codex brainstorm, CI fixing, negotiations, research lanes, and generic waterfall callers on default unless a scoped caller explicitly passes a role.

### UPDATED: python/collect_results.py

- Extend `RetryMeta` and `_parse_meta` with `outer_launcher_model_role`.
- When rebuilding retry argv for `agent launch-review`, pass `--model-role` from persisted meta when present.
- When rebuilding retry argv for `agent launch-codex-exec`, pass `--model-role` from persisted meta when present.
- Treat missing `OUTER_LAUNCHER_MODEL_ROLE` as `default` for backward compatibility with older metas.
- Do not mark retry metadata invalid solely because the role field is absent on legacy launches.

### UPDATED: python/agent_waterfall.py

- Add optional `--model-role default|review|vote|fix` to `agent dispatch-waterfall`.
- Thread `--model-role` only into Codex `agent launch-review` argv when the caller supplied it explicitly.
- Do **not** infer role from slot names (`voter-*`, `decomp-codex-*`, etc.). Generic waterfall callers without `--model-role` keep strong/default Codex behavior.
- Preserve current Cursor and Claude argv.
- Preserve global `--no-fallback` flag behavior for callers that pass it.
- Optional follow-on (only if needed for a one-slot voter-1 manifest): accept per-slot `no_fallback: true` in NDJSON rows and honor it during phase-2 fallback so a single-slot Cursor validity row cannot fall through to Codex. Prefer direct `agent launch-review --tool cursor` for voter-1 first; use one-slot `agent dispatch-waterfall --no-fallback` only when tests or call-site parity require waterfall-shaped launch metadata.
- Add shared helper `bind_manifest_slot_outputs(manifest_path, wf_kv) -> dict[str, SlotOutputBinding]` (or equivalent) exported for voter/panel callers:
  - Load manifest NDJSON rows in file order; key bindings by manifest `slot` field (e.g. `voter-2`, `voter-3`).
  - Read resolved winning paths from `ALL_OUTPUT_FILES_PATH` when present; fall back to tokenizing compressed `ALL_OUTPUT_FILES` only as a degraded legacy path.
  - For each manifest row, resolve the winning path by matching `row["output"]` exactly, by basename equality, or by phase suffix (`-phase2`, `-phase3`) on the manifest stem (same contract as `_output_for_phase` in this module).
  - Pair the winning tool from the compressed `ALL_OUTPUT_TOOLS` entry at the same index as the matched resolved path (not at manifest row index).
  - When a manifest row has no resolved match, consult `DROPPED_SLOTS_FILE` (tab-separated slot name in column 0) to distinguish dropped vs failed-empty.
  - Return per-slot `{path, tool, dropped}` so callers never zip compressed stdout positions onto fixed voter numbers.

### UPDATED: python/review_pipeline.py

- Remove `codex_slots_enabled = round_num < 2 or cursor_available != "true"`.
- Emit static Codex specialist rows whenever `codex_available == "true"`.
- Remove the round-2+ `codex-generic` row.
- Keep reviewer pruning intact.
- Rename/replace the `codex_slots_enabled` parameter on `_synthesize_dynamic_slots` with an explicit `codex_available == "true"` gate (or equivalent boolean passed from callers). Update all call sites so dynamic `dyn-*-codex` twins emit whenever Codex is present, including round 2+ with Cursor up.
- When calling `agent dispatch-waterfall` for the review panel, pass `--model-role review` explicitly.
- **Review-panel `--no-fallback` rule (explicit):** append `--no-fallback` only when `cursor_available == "true" and codex_available == "true" and round_num < 2`. Do not append it in round 2+ when both vendors are present. Do not append it solely because Codex is present and Cursor is absent.
- Update any counts, diagnostics, and tests that assumed one generic Codex reviewer in later rounds.
- In `review core` voter tally integration, change the missing-KV default tuple from `("cursor-validity", "cursor-plan-fidelity", "cursor-pragmatism")` to `("cursor-validity", "codex-plan-fidelity", "codex-pragmatism")`.
- Prefer shared voter-label constants with `python/voting.py` if that avoids drift.

### UPDATED: python/plan_review_panel.py

- Remove `_CODEX_GENERIC_MIN_ROUND` behavior.
- Emit Codex plan specialist rows for every round when Codex is present.
- Remove the round-2+ `codex-plan-generic` row.
- Keep Cursor rows unchanged.
- Keep dynamic rows unchanged except that Codex dynamic twins continue when available.
- When calling `agent dispatch-waterfall` for plan-review panel dispatch, pass `--model-role review` explicitly.
- For plan-review voter Codex launches through waterfall, pass `--model-role vote` explicitly on the voter waterfall invocation.
- Replace compressed `ALL_OUTPUT_FILES` index / raw tool-token routing for plan-review voters (current `if tool == "codex": voter_2_path = ...` pattern) with `bind_manifest_slot_outputs` keyed by manifest `slot` (`voter-2`, `voter-3`).

### UPDATED: python/agent_voters.py

- Replace `CURSOR_VOTER_SLOTS` hardcoded Cursor-only manifest with per-slot tool policy:
  - slot 1 / `voter-1`: primary `cursor`, label `cursor-validity`, output `cursor-validity-vote-output.txt`
  - slot 2 / `voter-2`: primary `codex`, label `codex-plan-fidelity`, output `codex-plan-fidelity-vote-output.txt`
  - slot 3 / `voter-3`: primary `codex`, label `codex-pragmatism`, output `codex-pragmatism-vote-output.txt`
- Add slot-policy constants for archetype, default label, default output basename, primary tool, and semantic label map per winning tool.
- **Split dispatch (blocking invariant):** do **not** launch all three voters through one fallback-enabled mixed manifest.
  - **Cursor-present path:** launch voter-1 via `_launch_voter1_cursor_only` using direct `agent launch-review --tool cursor` (no `--model-role`; validity stays on Cursor/composer-2.5). Do **not** pass `--no-fallback` to `launch-review`. Alternative only when needed: one-slot `agent dispatch-waterfall` with global `--no-fallback` and a single Cursor row. Launch voters 2–3 via a separate two-row manifest (`voter-2` codex, `voter-3` codex) through `agent dispatch-waterfall` **without** global `--no-fallback`, with `--model-role vote`.
  - **Codex-present / Cursor-absent path:** voter-1 stays on the existing Claude-only degraded launch. Render prompts for voters 2–3, write a two-row Codex-only manifest, run waterfall with `--model-role vote` and **without** global `--no-fallback`. Voter-1 must not be included in this manifest.
  - **Both externals down:** keep the existing Claude-only shrink path (voter-1 only; voters 2–3 skipped).
- Restructure `dispatch_voters` entry gate:
  - run an external-voter path when **either** `cursor_available == "true"` or `codex_available == "true"`, not only when Cursor is present
  - ensure `_make_voter_prompt_file` runs for voters 2–3 on the Codex-up / Cursor-down branch before building the two-slot manifest
- Add `_write_voter23_waterfall_manifest` (two Codex rows only) and `_launch_voter1_cursor_only` helpers; remove the old three-slot `_write_waterfall_manifest` that put voter-1 in the same waterfall as voters 2–3.
- `_launch_voter1_cursor_only` must build the same prompt/context argv as the old voter-1 slot and invoke `agent launch-review --tool cursor` directly; on failure, route to Claude fallback or degraded status without ever launching Codex for slot 1.
- After the voters 2–3 waterfall returns, call `bind_manifest_slot_outputs(manifest, wf_kv)` and bind `VOTER_2_PATH` / `VOTER_3_PATH` from the `voter-2` / `voter-3` slot keys. **Do not** zip compressed `ALL_OUTPUT_FILES` indices 0/1 onto voters 2–3. **Do not** mirror `plan_review_panel.py` raw tool-token routing (`if tool == "codex": voter_2_path = ...`).
- Derive semantic `VOTER_*_TOOL` from slot policy plus binding winning tool:
  - voter-2: `codex` → `codex-plan-fidelity`; `cursor` → `cursor-plan-fidelity`
  - voter-3: `codex` → `codex-pragmatism`; `cursor` → `cursor-pragmatism`
  - voter-1: always `cursor-validity` when Cursor launch succeeds; `claude` on both-externals-down path
- When a slot binding is empty or dropped, mark that voter `failed` before sentinels, status assignment, and parse-rate retry; probe the resolved winning path (including `-phase2`/`-phase3` suffix) on success paths.
- Recompute `expected_judges` from launched slot policy:
  - `3` when the Cursor-present three-judge path runs (voter-1 Cursor + voters 2–3 scheduled)
  - `3` when the Codex-up / Cursor-down path runs (voter-1 Claude + voters 2–3 Codex scheduled)
  - `1` only on the both-externals-down Claude-only shrink path
- Update `DispatchState` defaults to the new Codex-primary labels.
- Preserve degraded-panel warning and parse-rate retry behavior.
- Preserve both-vendors-down Claude fallback path for voter-1 only.

### UPDATED: python/voting.py

- Update default code-review voter tool labels to:
  - slot 1: `cursor-validity`
  - slot 2: `codex-plan-fidelity`
  - slot 3: `codex-pragmatism`
- Update helper mappings such as `voter_launcher_tool`.
- Keep parser compatibility for existing historical labels where feasible, so old logs remain readable.

### UPDATED: python/plan_quality.py

- For plan revision through `agent launch-review --tool codex`, pass `--model-role fix`.
- For plan validator/autofix through `agent launch-codex-exec`, pass `--model-role fix`.
- Keep Cursor and Claude tiers unchanged.
- Keep plan-prose edit semantics unchanged.

### UPDATED: python/review_and_fix.py

- For Codex review-fix application through `agent launch-codex-exec`, pass `--model-role fix`.
- Keep Cursor and Claude fallback tiers unchanged.
- Keep staging and commit logic unchanged.

### UPDATED: python/report_tokens_cost.py

- Add `("codex", "gpt-5.4-mini")` to `DEFAULT_RATE_TABLE_PER_M`:
  - input `0.75`
  - cache read `0.075`
  - output `4.50`
- Keep the default Codex display model as `gpt-5.5` unless the existing pricing flow already supports per-record model pricing.
- Do not expand token pricing scope beyond the new row unless tests show existing model-aware pricing is expected.

### UPDATED: .claude-plugin/plugin.json

- Update `userConfig.codex_model.description` to state it controls only the **strong/default** Codex model for untagged launches such as Step 2 implementer, brainstorm, and other callers that do not pass `--model-role`.
- Remove claims that this option controls review, sketches, or voting.
- Point operators to the role-specific env keys (`LARCH_CODEX_REVIEW_MODEL`, `LARCH_CODEX_VOTE_MODEL`, `LARCH_CODEX_FIX_MODEL`) documented in `docs/configuration-and-permissions.md`.
- Leave `codex_effort` description unchanged unless it also incorrectly claims voting control.

### UPDATED: docs/configuration-and-permissions.md

- Document the new role env keys and defaults.
- Clarify that `LARCH_CODEX_MODEL` remains the strong/default Codex model for implementer and brainstorm.
- Clarify that review/vote/fix roles use their own keys and ignore `LARCH_CODEX_MODEL`.
- Document that blank/whitespace role env fails at probe or launch preflight.
- Update model defaults and default-rate prose to mention `gpt-5.4-mini`.
- Update fixer policy prose for review-fix and plan-autofix Codex mini routing.
- Note that the shipped `codex_model` plugin option maps only to the default/strong role.
- Do not claim Cursor uses Mini.

### UPDATED: docs/external-reviewers.md

- Update roles table:
  - review panels use Codex mini by default for Codex slots when callers pass `--model-role review`
  - code-review plan-fidelity and pragmatism voters are Codex primary with Cursor fallback
  - validity voter remains Cursor primary and does not fall through to Codex
  - review-fix and plan-revision Codex fixers use the fix model key
- Fix the stale dynamic-scout-waterfall attribution:
  - do not list `/design` and `/implement` as live scout consumers if only standalone `/review` diff-mode still scouts live.
- Keep fallback taxonomy wording aligned with actual code.

### UPDATED: python/test_agents.py

- Add resolver tests for `review`, `vote`, and `fix` roles.
- Add tests that `LARCH_CODEX_MODEL` does not affect role-specific review/vote/fix resolution.
- Add tests for role-specific blank and control-character rejection.
- Add `agent model-args --codex-role` coverage.
- **Preserve default-role fallback contract:**
  - `resolve_model_args("codex", codex_role="default", default_model="custom")` resolves to `custom` when env and plugin option are unset.
  - `agent model-args --tool codex --default-model custom` (default role) emits `-m custom` when env and plugin option are unset.
  - `resolve_model_args("codex", codex_role="review", default_model="custom")` ignores `default_model` and resolves to the review default.
- Add probe coverage: blank `LARCH_CODEX_REVIEW_MODEL` fails Step 0 Codex probe instead of launching without model args.
- Update existing stubs if the `resolve_model_args` signature changes.

### UPDATED: python/test_launch_review.py

- Add coverage that `agent launch-review --tool codex --model-role review` passes the review model.
- Add coverage that no `--model-role` keeps the strong default.
- Add coverage that `codex-brainstorm` remains on the strong model.
- Assert launch `.meta` writes `OUTER_LAUNCHER_MODEL_ROLE` for role-tagged launches.
- Assert `agent launch-review` argparse rejects unknown flags such as `--no-fallback` (regression guard).
- Update monkeypatched `resolve_model_args` stubs to accept the new keyword.

### UPDATED: python/test_collect_results.py

- Add retry coverage for `agent launch-review` that replays `--model-role review`.
- Add retry coverage for `agent launch-codex-exec` that replays `--model-role fix`.
- Add legacy-meta coverage where missing role defaults to strong behavior only when meta omits the field.

### UPDATED: python/test_agent_waterfall.py

- Assert review-panel callers that pass `--model-role review` forward it to Codex `launch-review`.
- Assert voter dispatch callers that pass `--model-role vote` forward it to Codex `launch-review`.
- Assert generic waterfall launches without `--model-role` do **not** add cheap-role flags.
- Assert decompose / other non-review waterfall callers remain on default when they do not pass role metadata.
- Assert Cursor and Claude launches do not receive Codex model-role flags.
- Add `bind_manifest_slot_outputs` coverage:
  - two-row manifest with only row 1 (voter-3) succeeding resolves `voter-3` path/tool and leaves `voter-2` empty/dropped
  - phase-2 winning path (`*-phase2.txt`) resolves against manifest phase-1 basename
  - `DROPPED_SLOTS_FILE` marks a slot dropped when no resolved path exists

### UPDATED: python/test_review_pipeline.py

- Update round-2+ expected manifests to include full Codex specialists and dynamic Codex twins when Codex is present.
- Remove assertions that expect `codex-generic` collapse.
- Keep prune tests proving empty/pruned specialists can still drop out.
- Add tally integration coverage for missing `VOTER_2_TOOL` / `VOTER_3_TOOL` defaulting to `codex-plan-fidelity` / `codex-pragmatism`.
- Assert `--no-fallback` presence per round:
  - present when both vendors up and `round_num == 1`
  - absent when both vendors up and `round_num >= 2`
- Update `_synthesize_dynamic_slots` call-site stubs to use the new Codex-availability gate instead of `codex_slots_enabled`.

### UPDATED: python/test_plan_review_panel.py

- Update round-2+ expected manifests to include full Codex plan specialists.
- Remove or replace assertions that expect `codex-plan-generic`.
- Keep dynamic archetype assertions intact.
- Assert panel waterfall dispatch passes `--model-role review`.
- Assert plan-review voter binding uses manifest slot keys via `bind_manifest_slot_outputs`, not compressed stdout indices.

### UPDATED: python/test_agent_voters.py

- Replace the assertion that mixed voter waterfall always includes global `--no-fallback`.
- Assert voter-1 launches on a Cursor-only path via direct `agent launch-review --tool cursor` without `--no-fallback`, or via a one-slot `agent dispatch-waterfall --no-fallback` manifest; voter-1 is **not** in the voters 2–3 manifest.
- Assert voters 2–3 waterfall omits global `--no-fallback` and passes `--model-role vote`.
- Assert two-row manifest shape: both rows `tool: codex` on the Cursor-present path.
- Assert `bind_manifest_slot_outputs` maps `voter-2` / `voter-3` keys to `VOTER_2_PATH` / `VOTER_3_PATH`; **reject** tests that zip compressed `ALL_OUTPUT_FILES` index 0 to voter-2.
- Assert semantic label derivation on Codex→Cursor phase-2 fallback:
  - voter-2 winning `cursor` → `cursor-plan-fidelity`
  - voter-3 winning `cursor` → `cursor-pragmatism`
- Add **voter-2 dropped / voter-3 succeeds** coverage: compressed stdout contains only one path; `VOTER_3_PATH` binds voter-3 output, `VOTER_2_STATUS=failed`, parse-rate retry and tally inputs use the correct paths.
- Add Cursor-present voter-1 phase-1 failure coverage proving Codex is never launched for slot 1.
- Add Codex-unavailable fallback coverage: Codex down, Cursor up; slots 2 and 3 fall back to Cursor with flipped labels.
- Add Codex-up / Cursor-down coverage:
  - prompts rendered for voters 2–3
  - two-slot Codex waterfall launches
  - voter-1 stays Claude-only degraded path
  - slots 2 and 3 do **not** launch validity on Codex
  - `expected_judges == 3` with no false degraded warning when all three succeed
- Add explicit coverage that voter-1 never falls through to Codex when Cursor is absent or when Cursor launch fails at runtime.
- Add negative coverage that `_launch_voter1_cursor_only` never emits `--no-fallback` on an `agent launch-review` argv list.
- Keep validity voter Cursor expectations when Cursor is present.

### UPDATED: python/test_voting.py

- Update default voter tool expectations.
- Keep historical label parsing tests if old labels are still accepted.

### UPDATED: python/test_plan_quality.py

- Assert Codex plan revision/autofix launchers pass `--model-role fix`.
- Keep Cursor autofix assertions unchanged.

### UPDATED: python/test_review_and_fix.py

- Assert Codex review-fix launchers pass `--model-role fix`.
- Keep fallback-tier and staging tests unchanged.

### UPDATED: python/test_report_tokens_cost.py

- Assert the mini pricing row exists with the expected bucket rates.
- Do not require aggregate Codex defaults to change from `gpt-5.5`.

## Edge cases

- **Global strong override:** `LARCH_CODEX_MODEL=gpt-5.5` must not change review/vote/fix roles when their role-specific env keys are unset.
- **Role-specific override:** `LARCH_CODEX_REVIEW_MODEL=custom-mini` should affect only review launches.
- **Blank role env:** whitespace in `LARCH_CODEX_REVIEW_MODEL`, `LARCH_CODEX_VOTE_MODEL`, or `LARCH_CODEX_FIX_MODEL` should fail at Codex probe or launch preflight, not mid-panel.
- **`default_model` / `--default-model` contract:** when env and plugin option are unset, `codex_role="default"` must honor `default_model` (Python kwarg) and `agent model-args --default-model` before falling back to `CODEX_DEFAULT_MODEL`. Review/vote/fix roles must ignore that override.
- **Brainstorm:** existing brainstorm calls must stay strong because they do not pass a cheap role.
- **Manual launch-review:** direct `agent launch-review --tool codex` remains strong unless the caller passes `--model-role`.
- **Generic waterfall callers:** decompose panel / aggregator slots stay on default unless their caller explicitly passes role metadata.
- **Voter-1 isolation:** validity never launches on Codex, even when Cursor is down, Codex is up, or Cursor launch fails and phase-2 fallback would otherwise map `cursor` → `codex`.
- **Voter-1 launch flags:** `--no-fallback` is valid only on `agent dispatch-waterfall`, not `agent launch-review`. Direct Cursor launch for voter-1 needs no fallback flag.
- **Voters 2–3 fallback:** Codex down and Cursor up falls back to Cursor with `cursor-plan-fidelity` / `cursor-pragmatism` labels; both external vendors down degrades to Claude via existing paths.
- **Codex-up / Cursor-down:** voters 2–3 require explicit prompt rendering and a two-slot manifest; skipping the Cursor branch must not skip prompt generation for slots 2–3.
- **Manifest-slot binding:** resolve each manifest row by `slot` name and manifest `output` basename (including `-phase2`/`-phase3` winners); never assign compressed `ALL_OUTPUT_FILES[0]` to voter-2 by position alone.
- **Partial voter success:** when voter-2 is dropped or empty and voter-3 succeeds, only `VOTER_3_PATH` receives the sole resolved path; voter-2 stays failed.
- **Waterfall phase-2 outputs:** after Codex→Cursor fallback, status/parse-rate retry must probe the resolved winning path and semantic label, not the phase-1 basename or Codex-primary default label.
- **Collector retry parity:** retry relaunches must preserve the first attempt's `--model-role`.
- **Round pruning:** full Codex specialists every round should still be pruned by the existing reviewer-prune ledger.
- **Review-panel no-fallback:** round 1 with both vendors keeps `--no-fallback`; round 2+ with both vendors omits it; do not broaden `--no-fallback` to all rounds without an explicit policy change.

## Failure modes when non-trivial

- **Partial role tagging** can silently leave expensive Codex paths on `gpt-5.5`. Tests should inspect argv and `.meta` for every review/vote/fix launcher touched here, including collector retries.
- **Over-broad defaults** can downgrade brainstorm, implementer, or decompose slots. Keep cheap roles opt-in by scoped caller only.
- **Broken `default_model` contract** can regress harnesses or scripts that rely on `agent model-args --default-model` or Python callers passing `default_model=` into `resolve_model_args`. Keep the default-role ladder env → plugin → `default_model or CODEX_DEFAULT_MODEL`; add focused tests.
- **Invalid voter-1 argv** can break every Cursor-present run if `_launch_voter1_cursor_only` passes unsupported `--no-fallback` to `agent launch-review`. Use direct Cursor launch or one-slot waterfall only.
- **Single mixed voter waterfall** can let voter-1 validity fall through to Codex on Cursor failure. Enforce split dispatch and Cursor-only voter-1 launch; regression-test Cursor-present voter-1 runtime failure.
- **Compressed stdout index binding** can assign voter-3's sole successful output to `VOTER_2_PATH` when voter-2 is dropped, breaking parse-rate retry and tally on live fallback paths. Use `bind_manifest_slot_outputs`; regression-test voter-2 fail + voter-3 succeed.
- **Stale `expected_judges`** can emit false degraded warnings or miss real degradation on Codex-up / Cursor-down paths. Recompute from launched slot policy.
- **Missing Codex-up / Cursor-down prompt branch** can skip voters 2–3 entirely while reporting a one-judge panel. Gate prompt rendering and manifest build on `codex_available`, not `cursor_path`.
- **Leftover `codex_slots_enabled`** can suppress dynamic Codex twins in round 2+ or raise `NameError` after static-slot removal. Replace with `codex_available` at all `_synthesize_dynamic_slots` call sites.
- **Ambiguous review-panel `--no-fallback`** can change round-1 or round-2 behavior unintentionally. Pin the `round_num < 2` dual-vendor rule and test per round.
- **Stale plugin.json copy** can contradict per-role routing and confuse operators tuning review cost. Update `codex_model` description in the same PR.
- **Voter label churn** can break tally parsing or historical log rendering. Preserve compatibility where the parser accepts tool labels.
- **Round-2 manifest expansion** can increase reviewer count. Existing pruning should bound repeated useless reviewers.

## Testing strategy

- Run focused Python tests:
  - `python3 -m pytest python/test_agents.py`
  - `python3 -m pytest python/test_launch_review.py`
  - `python3 -m pytest python/test_collect_results.py`
  - `python3 -m pytest python/test_agent_waterfall.py`
  - `python3 -m pytest python/test_review_pipeline.py`
  - `python3 -m pytest python/test_plan_review_panel.py`
  - `python3 -m pytest python/test_agent_voters.py python/test_voting.py`
  - `python3 -m pytest python/test_plan_quality.py python/test_review_and_fix.py`
  - `python3 -m pytest python/test_report_tokens_cost.py`
- Run required repo checks:
  - `make lint`
  - `make py-lint`
  - `make py-test`
- Add an argv parity audit in the PR notes:
  - review panel Codex slots use `--model-role review`
  - voter Codex slots use `--model-role vote`
  - Codex fixers use `--model-role fix`
  - implementer, brainstorm, decompose, and generic waterfall callers without explicit role stay on default
  - default-role resolution still honors `default_model` / `--default-model` when env and plugin option are unset
  - collector retries replay persisted model role
  - voter-1 validity uses direct `agent launch-review --tool cursor` or one-slot waterfall `--no-fallback`; never `--no-fallback` on `launch-review`
  - voters 2–3 use separate fallback-enabled waterfall
  - voter 2–3 paths bind by manifest `slot`, not compressed stdout index
  - review-panel `--no-fallback` only on round 1 with both vendors present

## Acceptance

- `resolve_model_args("codex", codex_role=...)` resolves three new role keys: `LARCH_CODEX_REVIEW_MODEL`, `LARCH_CODEX_VOTE_MODEL`, `LARCH_CODEX_FIX_MODEL`, each defaulting to `gpt-5.4-mini`.
- Review, vote, and fix roles ignore a globally-set `LARCH_CODEX_MODEL` and ignore `default_model` / `--default-model`. The `default` role still honors `LARCH_CODEX_MODEL`, then the plugin option, then `default_model or CODEX_DEFAULT_MODEL` (`gpt-5.5`).
- The Step 2 Codex implementer and brainstorm stay on the strong default model.
- Plan review and code review run full Codex specialists every round; the round-2+ generic-Codex collapse is removed. Reviewer pruning still applies.
- Code-review plan-fidelity and pragmatism voters run on Codex (vote role) with Cursor fallback, then Claude when both vendors fail. The validity voter stays on Cursor and never falls through to Codex.
- Codex review-fix and plan validator-autofix launches use the fix role.
- `report_tokens_cost.py` includes a `("codex", "gpt-5.4-mini")` pricing row (input 0.75, cache read 0.075, output 4.50).
- Docs reflect the new keys and roles: `docs/configuration-and-permissions.md`, `docs/external-reviewers.md`, and `.claude-plugin/plugin.json` `codex_model`. The stale dynamic-scout-waterfall attribution to /design and /implement is corrected.
- Cursor reviewers and voters stay on `composer-2.5`; no role hosts Mini on Cursor.
- `make lint`, `make py-lint`, and `make py-test` pass. New and updated tests cover role resolution, the default_model contract, argv and `.meta` parity, collector-retry role replay, manifest-slot voter binding, and voter fallback paths.

diff_added: 870
diff_deleted: 250
mechanical_churn: false
diff_lines: 1120

## Test plan
(no test plan section in plan-file)
