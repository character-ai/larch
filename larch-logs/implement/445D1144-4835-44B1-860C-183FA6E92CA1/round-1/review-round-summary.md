# Review Round 1

- Mode: `diff`
- 5 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: voter-dispatch harness missing required `--round-num`
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: `scripts/test-prompt-template-invariants.sh` invokes plan-review `voter-dispatch` without the newly required `--round-num` flag. `make test-prompt-template-invariants` (and thus `make lint` / `test-harnesses-3`) fails at argparse before prompt assertions run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Add --round-num 1 to the harness invocation
  - From cursor-specialist-testing: Pass --round-num 1 in the harness command and update companion smoke docs if needed.
  - From codex-specialist-testing: Pass --round-num 1 in the harness command and update companion smoke docs if needed.


### FINDING_4: `_panel_slot_kind_from_env` classifies `dyn-*` slots as `plan-review` via `plan` substring
- **Reviewer(s)**: dyn-dyn-panel-env
- **Severity**: important
- **Concern**: `_panel_slot_kind_from_env()` classifies any slot whose name contains `"plan"` as `plan-review` before it checks the `dyn-*` specialist rule. A dynamic code-review slot like `dyn-migration-plan` is therefore logged as `plan-review`, not `specialist`. That mis-tags rows in `panel-prompt-sizes.tsv` and splits `measure_panel_cost` aggregates under the wrong `slot_kind`, so panel-tier density ranking can under-count specialist prompts and over-count plan-review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-panel-env: Treat `dyn-*` slots as specialists first (or match reserved static specialist slugs exactly), and reserve the `"plan" in lowered` heuristic for explicit plan-review slot names such as `cursor-plan-arch`, not arbitrary substrings.


### FINDING_7: `review_dispatch_panel` missing `round-<N>` subdirectory fallback for panel artifact dir
- **Reviewer(s)**: dyn-dyn-panel-env
- **Severity**: important
- **Concern**: Panel artifact routing always sets `panel_artifact_dir = review_tmpdir` and only treats the directory as round-local when `review_tmpdir.name` already matches `round-<N>`. The approved plan also required `review_tmpdir / f"round-{round_num}"` when round-scoped outputs live under that subdirectory but `--review-tmpdir` is the run root. That fallback is missing. Any caller that keeps per-round outputs under `round-<N>/` while passing the parent tmpdir will write `panel-prompt-sizes.tsv` beside the run root instead of under `round-<N>/`, diverging from the documented committed path `larch-logs/review/<RUN_ID>/round-<N>/panel-prompt-sizes.tsv` and from `measure_panel_cost()`'s round-scoped review scan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-panel-env: Mirror the plan's three-step resolver: use `review_tmpdir` when it is already `round-<N>`, else `review_tmpdir / f"round-{round_num}"` when that directory exists or is the round output root, else `review_tmpdir`; pass the resolved path to both `build_panel_dispatch_env()` and `--panel-artifact-dir`.


### FINDING_8: missing non-panel guard tests for `plan_scout` / decompose callers
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: important
- **Concern**: Plan-required tests that known non-panel `launch-review` callers (e.g. `plan_scout`, decompose) do not create `panel-prompt-sizes.tsv` are absent. Only env-forwarding and unit helper tests exist. A future change could set panel env globally or instrument scout/autofix launches while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Add a harness test that a known non-panel launch-review caller creates no panel-prompt-sizes.tsv.


### FINDING_9: dispatch integration tests do not assert `panel-prompt-sizes.tsv` row materialization
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: important
- **Concern**: Dispatch integration tests assert panel argv/env only, not TSV row materialization. Plan-requested count-based assertions that `panel-prompt-sizes.tsv` rows are produced for dispatch-panel specialists/voters are absent. Removing `append_panel_prompt_size` from launchers would not fail CI despite the feature requiring per-slot committed sizes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Add count-based harness tests that stub child launches and assert round-scoped panel-prompt-sizes.tsv rows with expected slot_kind and no prompt text.


