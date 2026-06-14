# Review Round 3

- Mode: `diff`
- 5 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: C3a1 plan-review port incomplete — core verbs still execute embedded legacy bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: `python/plan_review.py` and `python/plan_review_panel.py` delegate loop, tally, emit, panel, and voter dispatch to gzip/base64-embedded retired bash via `_run_legacy()` / `run_legacy_script()` and `_materialize_legacy_root()`, not native Python. On-disk script edits and greps no longer reflect runtime behavior; the C3a1 stdlib port goal is unmet and Step 3 still depends on opaque materialized shell (including `review-design-step3-loop.sh` in assets and `plan_review_panel.py` panel/voter paths).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-generic-output.txt: Replace the embedded legacy-root machinery with real Python implementations for the plan-review loop, tally, emit/finalize/preview, state, timing, Gate B dedup, panel dispatch, and voter dispatch. Delete the compressed assets and make tests exercise the Python code paths directly.
  - From dyn-retired-path-sweep-output.txt: Either document this as an explicit C1b-style legacy façade in `docs/python-migration.md` (like `legacy_review_shell`) until true in-process ports land, or finish porting loop/panel bodies so deleted scripts are not resurrected at runtime.


### FINDING_4: Deleted shell harness coverage not replaced — pytest and Makefile targets are thin aliases
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: Retired shell harnesses (`test-run-step3-review`, `test-plan-review-loop`, `test-persist-retally-step3-env`, `test-tally-plan-review`, etc.) were removed or retargeted, but `python/test_plan_review.py` only covers emit/finalize/preview, drift-baseline helpers, one step3-state case, and `--record-report-evidence`. Many Makefile `test-*` targets run the same unfiltered pytest while `docs/linting.md` still claims distinct cap, rollback, resume, tally, dedup, and preview coverage. Regressions in cap guard, `review-round-count.txt` persist/rollback on `tally-error` / `degraded-empty-collector`, terminal `LOOP_STATUS` / `STEP3_REVIEW_LOOP_STATUS` envelopes, MainAgent retally env refresh, and tally stdout KVs can ship undetected because those contracts still live inside embedded gzip bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-plan-cli-contracts-output.txt: Port the deleted shell harness cases into pytest (or keep the shell harnesses until parity exists), especially cap, rollback, retally env, and tally-error `SCOPE_ANCHOR_FILE` omission.


### FINDING_6: `drift_baseline_write_once` treats broken symlinks as already seeded
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: `drift_baseline_write_once` skips writing when `drift-baseline.env` exists or is a symlink (`path.exists() or path.is_symlink()`), including broken symlinks. Retired `lib-drift-baseline.sh` used `[[ ! -e "$baseline" ]]`, so bash still attempted a fresh write for broken symlinks. After cutover, `design-postplan-emit.sh` calls `plan-review drift-baseline write-once` and ignores exit code, so Step 2b can lack a baseline while later `plan check-size` drift logic diverges from pre-cutover behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-cli-contracts-output.txt: Match bash semantics: only skip when `path.is_file()`; if `path.is_symlink()` (broken or not), remove or replace it and write, or return a non-zero status that `design-postplan-emit.sh` surfaces as the historical WARN path.


### FINDING_7: `relevant-checks.sh` does not route `plan_review_panel.py` edits to panel harness targets
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: `python/plan_review_panel.py` and `python/test_plan_review_panel.py` have no `relevant-checks.sh` case arms. Panel-only or voter-dispatch diffs may only pull `test-plan-review` via shared `plan_review.py` cases, not `make test-plan-review-panel` or `make test-dispatch-plan-voters`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Add a `case` arm for `python/plan_review_panel.py|python/test_plan_review_panel.py` that appends `test-plan-review-panel` and `test-dispatch-plan-voters`, mirroring the `plan_review.py` → `test-plan-review` pattern.


### FINDING_8: Multiple operator-facing docs still cite retired plan-review shell entrypoints
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: Several docs and normative skill prose still name deleted scripts (`run-step3-review.sh`, `emit-design-plan-preview.sh`, `plan-review-loop.sh`, `design-step3-state.sh`, `emit-plan.sh`, etc.) or stale harness names while live wrappers call `python/cli.py plan-review …`. This misleads operators, can trip `make lint-retired-scripts`, and understates the real Step 3 entrypoint (`design-step3-review.sh` wrapping `plan-review run --mode loop`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Replace with `design-step3-entry-preview.sh` → `python/cli.py plan-review preview --variant step3` and `design-step4b-preview.sh` → `plan-review preview --variant gatec`, matching `docs/configuration-and-permissions.md`.
  - From dyn-retired-path-sweep-output.txt: Update the Step 3 sentence to the `python/cli.py plan-review run` entrypoint and name `design-step3-review.sh` only as the process-group wrapper.
  - From dyn-retired-path-sweep-output.txt: Point sentinel coverage at `python/test_plan_review.py` and/or `skills/design/scripts/test-design-step3-review.sh` / `design-step3-entry-preview.sh`, and drop the `.sh` harness name.
  - From dyn-retired-path-sweep-output.txt: Rewrite those references to `python/cli.py plan-review step3-state`, `python/plan_review.py`, `python/test_plan_review.py`, and `plan-review emit`, consistent with the updated wrapper cutover.
  - From dyn-retired-path-sweep-output.txt: Rewrite the Coverage section to the Python CLI + env-override model documented in the harness header and `python/test_plan_review.py`.


