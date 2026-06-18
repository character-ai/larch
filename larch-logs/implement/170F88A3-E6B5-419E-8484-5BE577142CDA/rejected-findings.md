### [rejected] FINDING_15

**Rejected subtype:** dismissed (0 YES)

### FINDING_15: architecture: `python/checks.py` SKILL.md relevant-checks rule omits migrated harnesses
- **Reviewer(s)**: dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: The `_DIRECT_TARGET_RULES` row for `skills/implement/SKILL.md` still routes only to `test-implement-structure` and `test-render-cost-line-callsites`. Preflight and Step 16–17 fences now live in SKILL as `python/cli.py implement preflight` and `python/cli.py implement step-16-17`, but edits to those fences do not trigger `test-implement-fence-shape`, `test-implement-preflight`, or `test-step-16-17` under `checks run-relevant`. SKILL-only fence regressions can pass relevant-checks while dedicated harnesses stay cold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-surface-output.txt: Extend the `skills/implement/SKILL.md` rule (or add sibling rules) to include `test-implement-fence-shape`, `test-implement-preflight`, and `test-step-16-17`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (0 YES)

### FINDING_16: architecture: `write-final-report.sh` still listed as active closeout authority
- **Reviewer(s)**: dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: The Extracted Script Registry still lists `write-final-report.sh` as an active closeout contract, but Step 17's live fence calls `python/cli.py implement step-16-17`, and `python/closeout.py` invokes `final-report write` directly. The thin Bash wrapper is no longer on the orchestrator path, leaving two documented authorities for the same Step 17 surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-surface-output.txt: Retire `write-final-report.sh` from the active registry (or mark it legacy-only), point the registry at `python/closeout.py` / `python/final_report.py`, and update `SECURITY.md` and sibling docs that still name the shell wrapper as the terminal summary writer.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_17: architecture: `docs/linting.md` harness table not retargeted for migrated closeout/finalize tests
- **Reviewer(s)**: dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: Harness docs were not fully retargeted with the Makefile changes. `test-step-18b-final-report` still documents only `python/test_pr_body.py`, but `Makefile:679` now runs `python/test_final_report.py` too. `test-finalize-sanity-check` still describes `session cleanup-tmpdir` coverage, but `Makefile:27` now runs `python/test_finalize.py -q -k cleanup_target_ok`. There are also no `docs/linting.md` rows for `test-step-16-17`, `test-implement-finalize`, or the retargeted `test-write-final-report`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-surface-output.txt: Update the linting table rows to match the new pytest-backed Makefile targets and add missing entries for the migrated closeout/finalize harnesses.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_18: architecture: `scripts/test-render-run-summary-callsites.sh` still greps `python/pr_body.py`
- **Reviewer(s)**: dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: After extracting final-report logic into `python/final_report.py`, this callsite harness still greps `python/pr_body.py` for `_final_report_token_fields` and `emergency_requested`. The canonical implementation now lives in `final_report.py`; `pr_body.py` only keeps compatibility re-exports. A regression in `final_report.py` could slip past this pin while `pr_body.py` shims still satisfy the grep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-surface-output.txt: Retarget the harness to `python/final_report.py` (and keep a minimal `pr_body.py` re-export check only if backward compatibility must stay pinned).


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (0 YES)

### FINDING_19: architecture: stale `agent-lint.toml` reachability comment for `render-review-phase-detail.sh`
- **Reviewer(s)**: dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: The exclusion comment still says `scripts/render-review-phase-detail.sh` is invoked at runtime from `write-final-report.sh`. Post-migration, `python/final_report.py` calls `review_phase_detail.render_implement_review_detail()` in-process. The reachability comment is stale and can mislead future migration or retirement work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-surface-output.txt: Update the comment to cite `python/final_report.py` (and `python/design_summary.py` where applicable) as the live callers.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: risk-integration: `python/closeout.py` `step_16()` does not record `write-rejected` CLI failures
- **Reviewer(s)**: dyn-closeout-flow-output.txt
- **Severity**: important
- **Concern**: `step_16()` always returns `0` after `review-and-fix write-rejected`, even when that subprocess exits non-zero (`stdout`/`stderr` are discarded and the return code is never checked). Round 4 added a `step_16_17()` `except Exception` path that logs Tool Failures for in-process crashes, but not for the ordinary CLI failure mode. The result is asymmetric closeout telemetry: Step 17 write failures are recorded in `execution-issues.md`, while Step 16 rejected-findings failures are not, so the final report can render without a matching rejected-findings batch and operators lose the execution-issues signal on that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-closeout-flow-output.txt: Capture the `write-rejected` return code inside `step_16()` (or immediately after the in-process call in `step_16_17()`), and on non-zero invoke `_append_failure()` with the same `Step 16 — rejected findings` / `Tool Failures` contract used elsewhere before continuing best-effort to Slack and Step 17.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_6: risk-integration: Step 18 teardown omits vendor-failure-diagnostics flush before log commit
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Step 18 teardown no longer flushes `vendor-failure-diagnostics.parts` into the `vendor-failure-diagnostics` run-log batch before committing logs. A vendor-agent failure before the normal pre-merge flush leaves only parts under `$IMPLEMENT_TMPDIR`; teardown commits `larch-logs` without staging them, then normal cleanup can delete the tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Call the existing vendor diagnostics staging path, for example `scripts/flush-vendor-failure-diagnostics.sh` or the equivalent `run_logs` helper, before `run_logs.commit_larch_logs(...)`, and add a teardown test with a `vendor-failure-diagnostics.parts/part.*` fixture.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_7: risk-integration: non-emergency missing-plan refusal untested in `python/test_preflight.py`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Non-emergency missing-plan refusal (`BLOCK_PRESENT=false`) has no pytest coverage. `/implement` could stop refusing missing `larch:plan` on the default path without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub plan-block read with `BLOCK_PRESENT=false`; assert `rc==2`, refusal message, and no `PLAN_PATH=` envelope


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

