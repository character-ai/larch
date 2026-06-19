## Goal
Implement issue #4765: [IMPLEMENTING] [BUG] Plan-review panel fails to launch: slot rows set inline prompt, not prompt_file.

## Implementation Plan
## Summary

The `/design` Step 3 plan-review panel launches **zero** reviewers on larch 51.1.5. The panel builder writes slot-manifest rows with an inline `prompt` field, but the `agent dispatch-waterfall` consumer only accepts `agent` or `prompt_file`. The first slot fails validation, the dispatcher aborts before launching anything, and Step 3 returns `panel-failed` (degraded). Every `/design` run on this version ships an **unreviewed** plan. This is a producer/consumer contract mismatch in `python/plan_review_panel.py` vs `python/agent_waterfall.py`, reproduced live on `main` (commit `41c27b965`, version 51.1.5). It is the **next** failure after #4747 (the `--mode plan-review` fix) unblocked the same dispatch path; both regressions trace to the #4632 / PR #4729 sh-to-py port of the `/design` Step 3 plan-review bodies.

## Original report

During a `/design 4758` run, Step 3 (plan review) returned immediately with `STEP3_REVIEW_LOOP_STATUS=panel-failed`, `DEGRADED_PANEL=1`, `ROUNDS_COMPLETED=1`, `ACCEPTED_COUNT=0`, and `AGGREGATOR_STATUS=skipped`. The first line of the review task output was:

```
dispatch-with-waterfall.sh: slot 'cursor-plan-arch' must set either agent or prompt_file
```

The operator asked for the root cause. Investigation showed the failure is deterministic (not a transient reviewer timeout or auth hiccup), affects all 14 slots in the manifest (8 static + 6 scout-dynamic), and is present in both the installed plugin cache and the dev tree on `main` (both 51.1.5). The plan-review panel is therefore broken for every `/design` run on this version, independent of which issue is being designed.

## Reproduction scenario

1. On larch 51.1.5, run `/design <issue-number>` with Codex and Cursor both present.
2. Let it reach Step 3 (plan review). The background loop driver (`python/cli.py plan-review run --mode loop`) returns almost immediately.
3. Observe `.step3-review-result.env` shows `STEP3_REVIEW_LOOP_STATUS=panel-failed` and the task stdout's first line is `dispatch-with-waterfall.sh: slot 'cursor-plan-arch' must set either agent or prompt_file`.

Minimal/unit reproduction (no external tools needed): build a manifest via `python/plan_review_panel.py` `_static_slot_rows(...)`, then parse it with `python/agent_waterfall.py`'s slot-parsing path. The first row raises `ValidationError: ... slot 'cursor-plan-arch' must set either agent or prompt_file`, because every produced row sets only `prompt`.

## Expected behavior

The static plan-review panel (Cursor + Codex across arch / innovation / pragmatic / requirements) plus any scout-dynamic `dyn-*` slots launch, run, and return findings; Step 3 proceeds through aggregation, voting, and tally. A missing prompt for one slot should at most degrade that slot, not abort the entire panel.

## Observed behavior

`agent_waterfall.py` rejects the first slot during manifest parsing and raises before launching any reviewer. The whole panel returns `panel-failed` / `DEGRADED_PANEL=1` with zero reviewers run. `/design` then bypasses Gate B and reaches Gate C with an unreviewed plan plus a degraded-review warning. No findings, no votes, no `voting-tally.md`.

## Root cause analysis

Producer and consumer disagree on the slot-row prompt field.

- **Producer** — `python/plan_review_panel.py`. `_slot_row()` (around lines 162-170) builds each slot dict with an inline `"prompt"` JSON string (defaulting to `Review the design plan with a {focus} lens.` when the render is empty). It never sets `prompt_file` or `agent`. `_static_slot_rows()` renders each prompt by running `python/cli.py render plan-review` and capturing **stdout** into a local `prompt` variable, computes the intended file paths `prompt_path = design / f"render-plan-cursor-{archetype}.prompt"` (line 47) and `codex_prompt_path` (line 78), but then **discards them** with `_ = prompt_path, codex_prompt_path` (line 99) and passes the inline text to `_slot_row`. The dynamic-slot loop does the same (`_slot_row(tool, slot, focus, round_dir / f"{slot}.txt", prompt)`).
- **Consumer** — `python/agent_waterfall.py`. Slot parsing (around lines 245-277) reads only `data.get("agent", "")` and `data.get("prompt_file", "")`. It never reads `prompt`. It then requires exactly one of `agent`/`prompt_file` to be non-empty and raises `slot '{slot}' must set either agent or prompt_file` otherwise. Downstream it passes `--prompt-file <path>` / `--agent-file <path>` to the launcher (lines ~335, ~347).

Because every produced row carries only `prompt`, the consumer rejects the first row and the panel never launches.

**Inference (not certain):** this looks like a refactor regression. The computed-but-discarded `prompt_path`/`codex_prompt_path` variables and the established voter pattern (see Evidence) both indicate prompts were once written to files and referenced via `prompt_file`. The reviewer-row path was switched to inline `prompt` without either (a) writing the prompt to its file and setting `prompt_file`, or (b) updating `agent_waterfall.py` to accept inline `prompt`.

**Relationship to #4747 (precursor) and #4632 / PR #4729 (origin):** this is the **same port** (#4632, landed by PR #4729) that introduced the #4747 `--mode plan-review` defect. #4747 fixed the earlier `--mode` validation failure (switched to `--mode description`), which had **masked** this one: with `--mode` corrected, the dispatcher now advances to the per-slot `agent`/`prompt_file` validation (`agent_waterfall.py` around line 272) and fails there instead. Both failures live in the same validator. #4747 also added stderr surfacing for panel dispatch, which is why this error (`slot 'cursor-plan-arch' must set either agent or prompt_file`) was visible in the Step 3 task output rather than silent. The offline harness stubs the waterfall, so neither regression was caught pre-merge — the same test-gap #4747 flagged.

## Evidence

- Generated manifest `plan-review-slots.ndjson` for the failing run: all 14 rows (`cursor-plan-arch`, `codex-plan-arch`, ... and `dyn-cursor-plan-stage-scope`, `dyn-codex-plan-lint-delta`, `dyn-cursor-plan-cleanup-partial`, etc.) have a non-empty `prompt` and no `prompt_file`/`agent`.
- `python/agent_waterfall.py` slot parse reads `agent = data.get("agent", "")` and `prompt_file = data.get("prompt_file", "")`; raises `must set either agent or prompt_file` when both are empty; never references a `prompt` key.
- `python/plan_review_panel.py` `_slot_row()` returns a dict whose only prompt-bearing key is `"prompt"`.
- Counter-example in the **same file**: the voter manifest path renders to stdout, writes it to a file via `prompt_file.write_text(proc.stdout, ...)`, and emits `{"slot": "voter-2", "tool": "codex", "output": ..., "prompt_file": str(codex_prompt)}` (and the cursor equivalent). The reviewer rows simply omit this step.
- Version parity: installed plugin and dev repo are both `51.1.5`; dev `main` is at `41c27b965`. The defect is live, not a stale cache.
- Test gap: `python/test_plan_review_panel.py` reads `plan-review-slots.ndjson` (asserts pruning/empty cases) but never asserts that each emitted row sets `prompt_file` (or feeds the manifest through the `agent_waterfall.py` slot validator), so the producer/consumer contract is unenforced.

## Affected files

- `python/plan_review_panel.py` — `_slot_row()` (emits inline `prompt`, no `prompt_file`); `_static_slot_rows()` (computes then discards `prompt_path`/`codex_prompt_path`; renders prompts to stdout); the dynamic-slot loop that calls `_slot_row` with inline prompts. This is the producer to fix.
- `python/agent_waterfall.py` — slot-row parser/validator that requires `agent` or `prompt_file` and ignores `prompt`. Either fix the producer to match this, or extend this to accept inline `prompt`.
- `python/test_plan_review_panel.py` — missing regression: no assertion that produced rows are launchable by the waterfall (each sets `agent` xor `prompt_file`).

## Suggested fix(es)

Preferred (Option A — match the existing voter pattern in the same file): in `_static_slot_rows()` and the dynamic-slot loop, write each rendered prompt to its prompt file (`render-plan-cursor-{archetype}.prompt`, `render-plan-codex-{archetype}.prompt`, and per-slug files for `dyn-*` slots), and have `_slot_row` emit `"prompt_file": str(prompt_path)` instead of inline `"prompt"`. Remove the `_ = prompt_path, codex_prompt_path` discard. Keep the empty-render fallback by writing the one-line fallback prompt to the file when the render returns empty/non-zero.

Alternative (Option B): teach `python/agent_waterfall.py` to accept an inline `"prompt"` key by materializing it to a temp prompt-file before launch. This is more invasive and diverges from the voter path; Option A is cleaner and localized.

Either way, add a regression test in `python/test_plan_review_panel.py` (per `.claude/rules/launcher-argv-test-coverage.md`) that builds a manifest via `plan_review_panel` and asserts every row is accepted by `agent_waterfall.py`'s slot parser (exactly one of `agent`/`prompt_file` set, prompt file readable).

## Open questions

- Was the switch to inline `prompt` intentional (pending a separate `agent_waterfall.py` update that never landed), or a pure refactor regression? This decides Option A vs B.
- Do the `dyn-*` scout slots need their own per-slug prompt files, or can they share the static naming scheme? (They go through the same `_slot_row`, so they need the same fix.)
- Should the panel **degrade gracefully** (drop a single unrenderable slot) rather than abort the whole panel when one row is malformed, as a defense-in-depth follow-up beyond the immediate field fix?

## Test plan
(no test plan section in plan-file)
