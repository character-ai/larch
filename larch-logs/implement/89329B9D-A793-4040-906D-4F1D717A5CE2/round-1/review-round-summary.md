# Review Round 1

- Mode: `diff`
- 3 accepted, 8 rejected (6 neutral)

## Accepted Findings

### FINDING_1: review_core passes unsupported --model-role to dispatch-panel
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: blocking
- **Concern**: `_review_core_body` appends `--model-role review` to `review dispatch-panel` argv (`python/review_pipeline.py:2115-2116`), but `dispatch_panel`'s accepted options set (`python/review_pipeline.py:969-994`) does not include `--model-role`. Any `/review` or `/implement` Step 5 path that reaches review core with findings fails at dispatch-panel with `unknown option: --model-role` before reviewers launch; mini Codex routing never runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove --model-role from dispatch_args (dispatch_panel already passes it to waterfall at 1273-1274), or add --model-role to dispatch_panel's options set.
  - From codex-specialist-correctness-output.txt: Remove `--model-role review` from `dispatch_args`; `dispatch_panel` already forwards `--model-role review` to `agent dispatch-waterfall` at `python/review_pipeline.py:1259-1275`.
  - From codex-specialist-testing-output.txt: Remove the unsupported flag from review_core or teach dispatch_panel to accept and forward/ignore it, then add a review-core regression test for this path.


### FINDING_5: _state_from_voter23_bindings ignores dropped bindings and canonical-path fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-codex-role-routing-output.txt
- **Severity**: important
- **Concern**: `_state_from_voter23_bindings` ignores `SlotOutputBinding.dropped` and substitutes canonical output paths and semantic tool labels when `binding.path` is empty (`binding2.tool or policy2.primary_tool`). In multi-round review with reused voter output filenames, a dropped voter-2 in round 2 can still read round-1 output plus `.done`, be marked launched, and corrupt tally/parse-rate inputs with wrong tool labels on fallback basenames.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Treat dropped or empty bindings as failed without canonical-path fallback; bind status and parse-rate retry only from resolved binding paths and tools.
  - From dyn-dyn-codex-role-routing-output.txt: When `binding.path` is empty or `binding.dropped` is true, leave the semantic tool empty or mark the slot failed before parse-rate retry; derive labels only from a non-empty binding tool.


### FINDING_8: Tally treats Cursor-down three-slot panel as one-judge
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Tally still treats Cursor-unavailable three-slot voting as a one-judge panel (`python/review_tally.py:685-687`). In Codex-up / Cursor-down runs, voter 1 is Claude and voters 2-3 are Codex; if Codex voters fail, one Claude vote can decide findings without a degraded warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Compute expected judges from launched policy: three when either external vendor is available in three-slot mode, one only when both externals are down.


