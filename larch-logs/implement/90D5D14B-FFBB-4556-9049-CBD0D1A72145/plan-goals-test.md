## Goal
Implement issue #4396: [IMPLEMENTING] [OPTIMIZATION] Cursor-first /design apply-agent; drop round-2+ generic Codex reviewer.

## Implementation Plan
## Plan

Direct inspection only. `approach-synthesis.txt` content is `NO_SKETCHES`.

## Approach

- Make the **/design apply-agent** Cursor-first.
- Remove the **round-2+ generic Codex reviewer** from both review panels.
- Keep **Codex as fallback** for Cursor reviewer rows when normal waterfall fallback is enabled.
- Keep **Claude as final fallback**.
- Keep existing `{tier}-plan-autofix` timing labels.
- Treat `python/legacy_review_shell/dispatch-panel.sh` as the **functional /review panel-layout authority**.
- Treat `python/review_pipeline.py` as a **CLI façade/entrypoint**, not a panel-layout authority.

## Files to modify/create

### UPDATED: python/plan_quality.py

- In `revise_plan_with_waterfall_main`, change the unified-diff attempt order:
  - From `codex`, `cursor`, `claude`
  - To `cursor`, `codex`, `claude`
- In the ord-4 file-replacement fallback loop, use:
  - `cursor`, `codex`, `claude`
- Do not change:
  - `f"{tier}-plan-autofix"` timing-task-kind strings
  - patch extraction
  - file-replacement fallback behavior
  - `claude` as final tier

### UPDATED: python/test_plan_quality.py

- Update tests that pin revise-waterfall tier order.
- Audit revise-waterfall tests with targeted greps for:
  - `REVISE_TIER_1_`
  - `codex-output.txt`
  - `--cursor-present false`
- Account for `_run_revise` defaulting to Cursor absent:
  - If a test means “first available external succeeds” with default Cursor absent, expect Codex on `REVISE_TIER_2_*`, not tier 1.
  - If a test means “tier 1 succeeds,” set Cursor present and stub `LARCH_TEST_LAUNCH_CURSOR_REVIEW`.
- Rename any test names that still describe Codex as tier 1, including the former tier-1 failure case if it now exercises Codex tier 2.
- Change expected winner/path assertions from Codex to Cursor where the first successful attempt is now tier 1.
- Update fake launcher cases that key off `codex-output.txt` when they are meant to exercise tier 1.
- Add or adjust an order assertion so regressions show the intended sequence:
  - initial pass: `cursor`, `codex`, `claude`
  - fallback pass: `cursor`, `codex`, `claude`
- Keep assertions that both external attempts include:
  - `--timing-task-kind cursor-plan-autofix`
  - `--timing-task-kind codex-plan-autofix`

### UPDATED: python/legacy_review_shell/dispatch-panel.sh

- This is the **sole functional /review panel-layout edit**.
- Remove the round-2+ `codex-generic` manifest row.
- Keep round-1 Codex specialist rows when Codex is available.
- Keep round-2+ Cursor specialist rows when Cursor is available.
- Keep round-2+ Codex specialist replacement rows only when Cursor is unavailable and Codex is available.
- Keep normal waterfall fallback for round 2+ with both vendors present.
  - Cursor row failures can still fall back to Codex or Claude.
  - Do not launch a dedicated generic Codex reviewer.
- Keep round-1 `--no-fallback` behavior unchanged.
- Keep `codex_slots_enabled` behavior:
  - Round 1 with Codex available: Codex specialists run.
  - Round 2+ with Cursor unavailable and Codex available: Codex specialists run as replacement.
  - Round 2+ with both vendors available: Cursor specialists only.
- Update comments and static counts to avoid claiming a generic Codex slot exists.

### UPDATED: python/plan_review.py

- Update the gzip-embedded retired `skills/design/scripts/dispatch-plan-review-panel.sh` asset.
- In the embedded script:
  - Remove or force-disable `codex_generic_enabled`.
  - Remove the `codex-plan-generic` manifest row block.
  - Update dynamic prompt `vendor_note` so round 2+ with both vendors says Cursor-only, not Cursor + Codex.
  - Keep `codex_slots_enabled` for round-1 Codex specialists and Cursor-unavailable replacement rows.
  - Keep normal waterfall fallback in round 2+ with both vendors present.
- Regenerate the embedded blob from the modified decoded script.
- Do not add a retired on-disk shell script back to the repo.

### UPDATED: python/test_plan_review_panel.py

- Add coverage for `/design` panel dispatch with both vendors and `--round-num 2`.
- Assert the manifest contains:
  - `cursor-plan-arch`
  - `cursor-plan-innovation`
  - `cursor-plan-pragmatic`
  - `cursor-plan-requirements`
- Assert the manifest does not contain:
  - `codex-plan-generic`
  - `codex-plan-arch`
  - any `dyn-codex-plan-*` rows for round 2+ with Cursor present
- Keep or add coverage that round 1 with both vendors still emits 8 static rows.
- Keep or add coverage that Cursor-unavailable round 2 emits Codex specialist rows.

### UPDATED: python/test_review_pipeline.py

- Add or update coverage for `/review dispatch-panel` with both vendors and `--round-num 2`.
- Assert the manifest has Cursor specialist rows only.
- Assert it does not contain `codex-generic`.
- Keep coverage that:
  - round 1 with both vendors passes `--no-fallback`
  - round 2+ with both vendors does not pass `--no-fallback`
  - Cursor-unavailable round 2 still emits Codex specialists

### UPDATED: docs/review-agents.md

- Update `/design` prose:
  - Round 1 uses available external specialists.
  - Round 2+ with both vendors uses Cursor specialists.
  - Codex remains a fallback through normal waterfall.
  - Both externals absent still uses one generic Claude reviewer.
- Update `/review` prose the same way.
- Remove the claim that one generic Codex reviewer is emitted from round 2 onward.
- Fix the stale issue citation while editing this paragraph.
- Name `python/legacy_review_shell/dispatch-panel.sh` as the active `/review` panel-layout authority.
- Name `python/cli.py review dispatch-panel` and `python/review_pipeline.py` as entrypoint/facade surfaces only.

### UPDATED: skills/design/references/plan-review.md

- Update the contract text:
  - Round 1: available vendor rows per static archetype.
  - Round 2+: Cursor specialists when Cursor is present.
  - Codex specialists only when Cursor is absent.
  - No `codex-plan-generic` slot.
- Keep the existing voter contract unchanged.
- Keep the both-absent generic Claude fallback unchanged.
- Keep normal fallback restored from round 2 onward.

### UPDATED: skills/design/SKILL.md

- Update the top-level panel summary.
- Remove “plus one generic Codex reviewer” from the round-2+ description.
- Preserve the reviewer-prune wording.

### UPDATED: skills/review/SKILL.md

- Update Step 2 panel prose.
- Remove references to the round-2+ generic Codex reviewer.
- State that round 2+ uses Cursor specialists when Cursor is available, with Codex fallback through the waterfall.
- Keep the Cursor-unavailable Codex replacement-specialist behavior.
- Update the round-5 sentence accordingly.

### UPDATED: skills/shared/topology.tsv

- Update `design.plan_review.dynamic_archetypes` to say dynamic slots are vendor-gated by round.
- Update `design.plan_review.panel_slots` to mention round-1 dual vendor, round-2+ Cursor-first static/dynamic rows, and fallback.
- Update `implement.review_and_fix.panel_hard` to mention:
  - round-1 dual-vendor hard panel when both vendors are present
  - round-2+ Cursor specialist rows when Cursor is present
  - Codex specialist replacement rows only when Cursor is absent
  - Codex and Claude fallback through the normal waterfall
- Name `python/legacy_review_shell/dispatch-panel.sh` as the `/review` hard-panel row authority.
- Keep `python/review_pipeline.py` described only as an entrypoint/facade if referenced.

### UPDATED: docs/topology.md

- Regenerate with:

```bash
python3 python/cli.py generate topology-docs
```

## Edge cases

- **Cursor absent**: `/design` revise-waterfall skips Cursor tier 1, then tries Codex tier 2, then Claude.
- **Codex absent**: `/design` revise-waterfall tries Cursor, then skips Codex, then Claude.
- **Both externals absent**: `/design` panel review still emits the generic Claude reviewer where it already did.
- **Round 2+ Cursor failures**: no generic Codex slot launches, but normal waterfall fallback can still retry Cursor rows through Codex or Claude.
- **Dynamic archetypes**: round 1 can still fan out to Cursor and Codex. Round 2+ with Cursor present should emit Cursor dynamic rows only.
- **/review authority drift**: functional panel edits must land in `python/legacy_review_shell/dispatch-panel.sh`, not only in `python/review_pipeline.py`.

## Failure modes

- **Embedded asset drift**: `python/plan_review.py` contains gzip-embedded retired bash. Decode, modify, re-embed, then verify with `python/test_plan_review_panel.py`.
- **Accidental loss of Codex fallback**: do not set `--codex-present false` or equivalent in round 2+ with both vendors. Remove only the generic reviewer slot.
- **Stale topology**: update both `/design` topology rows and `implement.review_and_fix.panel_hard`, then regenerate `docs/topology.md`.
- **Stale revise-waterfall tests**: tests may still assume Codex is tier 1 because `_run_revise` defaults Cursor absent. Either enable Cursor for tier-1 assertions or expect Codex on tier 2.
- **No-op /review edit**: editing only `python/review_pipeline.py` cannot remove `codex-generic`. The manifest block must be removed from `python/legacy_review_shell/dispatch-panel.sh`.
- **Weak acceptance-rate validation**: broad fluff-analysis output does not prove low value for generic Codex slots. The validation must report `n` and acceptance rate specifically for `codex-generic` and `codex-plan-generic`.

## Testing strategy

- Run focused tests:

```bash
python3 -m pytest python/test_plan_quality.py -q
python3 -m pytest python/test_plan_review_panel.py -q
python3 -m pytest python/test_review_pipeline.py -q
```

- Run Makefile targets:

```bash
make test-revise-plan-with-waterfall
make test-dispatch-plan-review-panel
make test-dispatch-panel-core
make test-dispatch-panel-core-dynamic
make test-fluff-analysis-corpus
```

- Run the requested broad fluff-analysis validation:

```bash
python3 skills/fluff-analysis/scripts/fluff-analysis.py --log-root larch-logs --min-group 1
```

- Add a targeted validation step for the removed generic Codex slots:
  - Report `n` and acceptance rate for `codex-generic`.
  - Report `n` and acceptance rate for `codex-plan-generic`.
  - Use either a small read-only filter over the same records or an explicit reviewer-slot breakdown in the fluff-analysis script.
  - Record the exact command and output in the implementation summary or PR notes.
- Run standard repo checks:

```bash
make py-lint
make py-test
make lint
```

diff_added: 115
diff_deleted: 70
mechanical_churn: false
diff_lines: 185

## Test plan
(no test plan section in plan-file)
