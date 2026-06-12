### FINDING_1: Step 5 in-loop timing can double-count with deferred `--record-only`
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds `_emit_implement_round_timing_row` on the `main-agent-required` lint-fix stall path in `review-implement-step5-loop.sh`, but that branch still calls `step5_persist_round_start` and exits without in-loop emit today; the stall orchestration path still invokes `step-5-resume.sh --record-only`, which records another row when `round-start-s` exists. `record-implement-review-round-timing.sh` dedupes only identical `(round, start_s, end_s)` tuples, so an in-loop row with one `end_s` plus a later deferred row with a different `end_s` can both land for the same round and corrupt the timing ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Either align with adjacent terminal lint branches and also teach `step-5-resume.sh` / `record-implement-review-round-timing.sh` to skip when a Step 5 round row already exists, or keep defer-only and fix why deferred recording fails for this branch instead of emitting in-loop.
  - From Codex-Pragmatic: Revise the plan so this path has one timing writer only. Either stop persisting round-start after the in-loop emit for this branch, or make step-5-resume/record helper skip when a row already exists for the same round/start. Update the existing Step 5 harness expectation accordingly.
  - From Cursor-Requirements: Gate `--record-only` when `timing-ledger.tsv` already has a `round` row for that `FINAL_ROUND_NUM` and `round-start-s`, or document and implement an explicit skip for `lint-fix-main-agent-required` once in-loop emission is added
  - From Codex-Requirements: Revise the plan to avoid leaving round-start-s for this terminal lint-fix stall, or make step-5-resume skip when a row for that round already exists, and update the existing Step 5 test expectation accordingly


### FINDING_2: Plan omits Step 5 harness updates that pin defer-only timing contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `test-review-and-fix.sh` `lint-fix-terminal-tail` (lines 3417–3428) asserts `timing-ledger.tsv` must not exist after loop exit, requires `round-start-s` for deferred orchestrator timing, and manually simulates `record-implement-review-round-timing.sh`. Implementing the proposed one-line in-loop emit without updating this case (and related timing tests) will fail CI even if production behavior is intentionally changed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/review-and-fix/scripts/test-review-and-fix.sh` to rewrite `lint-fix-terminal-tail` to expect an in-loop timing row (and drop the manual deferred-orchestrator simulation), or change the case to assert idempotent single-row behavior if both paths remain.
  - From Cursor-Innovation: Add `### UPDATED:` entries for `test-review-and-fix.sh` and `test-review-implement-step5-loop-timing.sh`; flip assertions to expect in-loop timing (or drop defer-only checks) and list both in Testing strategy
  - From Cursor-Pragmatic: Add test-review-and-fix.sh (and test-review-implement-step5-loop-timing.sh) to Files to modify/create; flip the lint-fix-main-agent-required case to assert exactly one in-loop row and document the new contract


### FINDING_3: Partial-upgrade `larch-run.sh` test may miss the real resume-plan-tail regression
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: Item 5 asks to catch the case where `plugin-root.env` exists but `larch-run.sh` is absent during `--resume-plan-tail`. The plan permits calling `_write_larch_run_sh` directly with only `plugin-root.env` in the temp dir. That bypasses `bootstrap.py`'s resume-tail branch, which requires `session-env.sh` before the `plugin-root.env` check (lines 338–347) and fails `resume-plan-tail-sentinel` when `plan.txt` or `feature-description.txt` is missing (lines 440–441). A direct-writer test can pass even if resume bootstrap stops emitting the launcher when `plugin-root.env` already exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify minimal resume fixtures (`session-env.sh`, `plan.txt`, `feature-description.txt`, optional `session-id`) or pin the test to `python.bootstrap._write_larch_run_sh` only and state that choice explicitly in the plan.
  - From Codex-Arch: Make the partial-upgrade case create session-env.sh plus plugin-root.env with larch-run.sh absent, then exercise bootstrap resume-tail behavior via bootstrap_main/_phase_infra with stubs or an equivalent infra invocation using resume_plan_tail=True. Use direct _write_larch_run_sh calls only for standalone launcher dispatch assertions.
  - From Codex-Innovation: For the partial-upgrade case, require invoking the resume bootstrap path, either skills/implement/scripts/step-0-bootstrap.sh --mode resume or python.bootstrap.run_bootstrap with resume_plan_tail=True, with existing plugin-root.env, absent larch-run.sh, and minimal session/plan fixtures. Use _write_larch_run_sh directly only for generic launcher dispatch tests.



