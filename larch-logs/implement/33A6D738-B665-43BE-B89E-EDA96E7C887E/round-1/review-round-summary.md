# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Codex per-slot `model_role` overrides discarded at launch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, codex-generalist-output.txt
- **Severity**: important
- **Concern**: `_parse_slot_row` no longer reads row-level `model_role`, `Slot` has no `model_role` field, and `_launch_slot` forwards only `opts.model_role` to every Codex launch. Generic Codex manifest rows from `review_pipeline.py` and `plan_review_panel.py` still emit `"model_role": "default"`, but round 2+ `/design` and `/review` panels pass global `--model-role review` (or `vote`). The generic Codex reviewer therefore runs as `review`/`vote` instead of `default`, changing model behavior and cost relative to the specialist slots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore slot.model_role or opts.model_role merge in _launch_slot for Codex, or add a launch-level test asserting generic slot gets --model-role default.
  - From codex-specialist-correctness-output.txt: Restore Slot.model_role and launch codex slots with slot.model_role or opts.model_role
  - From codex-specialist-edge-cases-output.txt: Restore the slot-level fallback, for example slot.model_role or opts.model_role, and keep the CLI option as the default only when the slot omits a role.
  - From codex-specialist-testing-output.txt: Restore per-slot precedence, for example effective_role = slot.model_role or opts.model_role
  - From codex-generalist-output.txt: Restore `Slot.model_role`, parse and validate row-level `model_role`, and launch Codex with `slot.model_role or opts.model_role`; restore the removed `test_dispatch_waterfall_slot_model_role_overrides_global_for_codex` coverage.


### FINDING_2: Static coverage gate ignores generic Codex reviewer output
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_static_slug_for_file` only matches `cursor|codex)-specialist-(.+)-output.txt`, so `codex-generalist-output.txt` is not mapped to the `generalist` slug. `_static_coverage_reason` therefore does not treat the generic Codex row as expected static coverage. On round 2+ panels with both vendors present, a missing or failed generic Codex reviewer can still leave `STATIC_DISPATCH_OK=true` when specialist rows succeed, so `check_reviewer_failure_threshold` may pass without any generic Codex result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Restore the generalist slug mapping or add an explicit expected-slug branch for that row
  - From codex-specialist-edge-cases-output.txt: Keep the generalist slug mapping for codex-generalist-output.txt when that row exists in the manifest, and preserve the success, failure, and straggler-dropped handling for that slug.
  - From codex-specialist-testing-output.txt: Keep the generic basename in the static slug mapping or add an explicit generic-row coverage branch


