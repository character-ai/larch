# Review Round 1

- Mode: `diff`
- 8 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_2: Step 3 SKILL.md still documents Codex/Cursor/Claude reviewer fallback after --no-fallback dispatch
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Step 3 SKILL prose still describes Codex/Cursor/Claude reviewer fallback though dispatch now always uses `--no-fallback`. An operator following SKILL.md expects Claude backfill when both vendors are down, but panel dispatch drops all reviewer rows. This misdiagnoses intentional row drops as panel failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Replace fallback sentence with no-fallback drop-rows contract matching plan-review.md.
  - From cursor-specialist-edge-cases: Replace the fallback sentence with the no-fallback contract from plan-review.md.


### FINDING_3: Missing unit test for tool-absent static coverage excuse in review_core_body.py
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: The plan-requested `tool-absent` static-coverage excuse was implemented in `python/larch/review/review_core_body.py` but has no regression test. A future change to excuse parsing could restore `panel-failed` on one-vendor-down round-1 panels under always `--no-fallback` without CI signal, blocking review on a supported degraded path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add test_static_coverage_reason_excuses_tool_absent_static_slot parallel to straggler test.
  - From cursor-specialist-edge-cases: Add test_static_coverage_reason_excuses_tool_absent_static_slot mirroring the straggler-dropped test.
  - From cursor-specialist-testing: Add a test mirroring test_static_coverage_reason_excuses_straggler_dropped_static_slot that uses reason tool-absent in DROPPED_SLOTS_FILE and asserts _static_coverage_reason returns empty.


### FINDING_5: LARCH_CODEX_REVIEW_MODEL docs stale after reviewer slots switched to model_role=default
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-generalist
- **Severity**: important
- **Concern**: `docs/configuration-and-permissions.md` still says reviewer slots default to `gpt-5.4-mini` via `LARCH_CODEX_REVIEW_MODEL`, but specialist reviewer rows now use `model_role=default` (`gpt-5.5`). Operators tuning `LARCH_CODEX_REVIEW_MODEL` to affect the main reviewer panel will see no effect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Document default-role gpt-5.5 for Codex specialist reviewers; scope LARCH_CODEX_REVIEW_MODEL to voters/fixers only.
  - From codex-generalist: Document that reviewer specialist rows use the default Codex role, and reserve `LARCH_CODEX_REVIEW_MODEL` for launch sites that still pass the review role.


### FINDING_6: tool-absent excuse at slug level is too broad in _static_coverage_reason()
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Excusing every `tool-absent` drop at the slug level in `python/larch/review/review_core_body.py:155-159` is too broad. If one vendor is absent and the surviving reviewer for that archetype fails or is non-substantive while other slots still keep the failure threshold under half, `_static_coverage_reason()` removes that archetype from `missing` and the panel can pass with no successful reviewer output for that slot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: do not add `tool-absent` to the whole-slug excusal set. Either scope the excusal to the exact dropped slot, or only suppress `panel-failed` when the surviving row for that slug produced a successful output.


### FINDING_7: panel_pruned_empty false on genuinely empty round-2 manifest
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: `panel_pruned_empty` in `python/larch/review/review_prune.py:290` only becomes true when pruning removed at least one row. A genuinely empty round-2 manifest still falls through to `review_dispatch_panel.py:700-714` and launches the waterfall instead of converging. That breaks the cap-2 contract for "no reviewers eligible for round 2" and can still surface `panel-failed` on an empty panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: treat an empty eligible set as prune-empty on round 2 even when the input manifest was already empty, and short-circuit the dispatch path before waterfall launch whenever round-2 pruning leaves zero reviewers.


### FINDING_8: Plan-listed prune-empty execute_round tests still target round 3 instead of round 2
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: Plan-listed `execute_round` prune-empty tests in `python/tests/review/test_plan_review_round.py:748-775` were not retargeted from round 3 to round 2. Round-2 prune-to-empty ledger absence and latest-reviewer-status clearing can regress without failing CI because production never hits round 3 after cap=2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Retarget prune-empty execute_round tests to round_num=2 and prune_round_num=2 with round-2 artifact paths.


### FINDING_9: Missing CLI rejection tests for --max-archetypes 2 and 3
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: Plan-required CLI rejection tests for `--max-archetypes 2` and `3` are missing from `python/tests/design/test_plan_scout.py`. `filter_manifest_main` now enforces 0..1, but a regression restoring 0..3 validation would not be caught by current tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add filter_manifest_main cases for caps 2 and 3 expecting exit 2 and the 0-1 usage error text.


### FINDING_10: agent check-reviewers probes Codex review role but panel slots use default role
- **Reviewer(s)**: codex-generalist
- **Severity**: important
- **Concern**: Codex reviewer slots now force `model_role="default"` in `python/larch/core/config.py:271-295`, but `agent check-reviewers` still probes Codex with `codex_role="review"` in `python/larch/agents/_auth.py:398`. With an invalid `LARCH_CODEX_MODEL` and valid `LARCH_CODEX_REVIEW_MODEL`, Step 0 can mark Codex healthy, then every Codex reviewer slot fails at launch and is dropped under `--no-fallback`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: Make the health probe validate the effective Codex model role used by reviewer-panel slots, or probe/cache per Codex model role and request `default` for these panels.
