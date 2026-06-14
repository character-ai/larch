# Review Round 2

- Mode: `diff`
- 13 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: MAV apply uses full pre-coder snapshot instead of head-only semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: MAV apply calls `_write_pre_coder_snapshot`, which captures full tracked state via `_snapshot_pre_coder_tracked_state`. The deleted shell path only wrote `pre-coder-head.txt` for MAV handoff. Stage-path / carryover logic can therefore classify coder fixes on paths already dirty at snapshot time as pre-coder carryover, omit them from the round commit, and return `CODER_STATUS=applied` with fixes still unstaged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add MAV-only head snapshot helper (head + 0444, no `_snapshot_pre_coder_tracked_state`) and test absence of tracked snapshot files
  - From cursor-specialist-edge-cases-output.txt: Add a head-only snapshot helper for mav-apply (`pre-coder-head.txt` only) and pytest that tracked snapshot files are not created in MAV mode.


### FINDING_10: `main-agent-vote-required` returns without `STEP5_REVIEW_LEDGER_*` KVs
- **Reviewer(s)**: codex-generic-output.txt, dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: The `main-agent-vote-required` handoff emits the final `STEP5_REVIEW_STATUS` envelope and returns immediately without calling `_record_escalation_if_needed()`. That helper owns `STEP5_REVIEW_LEDGER_*` emission for MAV (`STEP5_REVIEW_LEDGER_SITE=step5-mav`, `STEP5_REVIEW_LEDGER_TRIGGER=main-agent-vote-required`, etc.). The deleted `run-step5-review.sh` wrapper always printed those ledger KVs; folding the launcher into `step5()` moved that responsibility here, but the MAV branch never runs it. Downstream `/implement` orchestrator and stall-recovery consumers expect those KVs on stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Call the ledger emission path for `main-agent-vote-required` before returning, matching the existing helper branch at `python/review_and_fix.py:1634-1645`.
  - From dyn-step5-contract-output.txt: After `_emit_step5_envelope(...)` on the `main-agent-vote-required` path, call `_record_escalation_if_needed(implement_tmpdir, "main-agent-vote-required", result.rc, stderr_path)` (or extract a shared MAV-ledger helper) before returning. Add pytest asserting the full `STEP5_REVIEW_LEDGER_*` bundle on that exit, mirroring the removed `test-run-step5-review.sh` MAV case.


### FINDING_11: `mav-apply` does not require findings file to exist
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `mav-apply` validates only that `--findings-file` is non-empty, not that it exists. A stale MAV accepted-findings path can reach Step 5; `_count_findings()` treats the missing file as zero findings; `mav-apply` exits `0` with `REVIEW_AND_FIX_STATUS=mav-apply-done` and `CODER_STATUS=skipped` without applying anything.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: In `_preflight_step5`, require `Path(args.findings_file).is_file()` for `--mode mav-apply`, preserving the old hard-fail contract.


### FINDING_12: Dynamic archetypes default changed from `3` to `0` in implement mode
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Step 5 now defaults dynamic archetypes to `0` when CLI, process env, and session env are empty. The shell implementation defaulted implement-mode review rounds to `3`, so a normal Step 5 run with no explicit `LARCH_DYNAMIC_ARCHETYPES_MAX` silently disables dynamic review slots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Preserve the old precedence: CLI, non-empty process env, session env, then `3` when running with an implement tmpdir, otherwise `0`.


### FINDING_13: Rejected findings no longer aggregated across rounds
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Rejected findings are no longer aggregated across rounds. Round 1 rejected finding A and round 2 rejected finding B overwrite the root `rejected-findings-full.md` with the latest round instead of rebuilding the multi-round `rejected-findings.md`, so Step 16 can report only B.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Port the old `write_rejected_findings_aggregate` behavior and rebuild the root rejected-findings artifact from all `round-*` directories after each round.


### FINDING_14: Handoff rounds record timing immediately and skip `round-start-s`
- **Reviewer(s)**: dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: Handoff rounds (`main-agent-vote-required`, `coder-main-agent-required`) call `record_round_timing()` immediately after each round and never write `round-N/round-start-s`. The retired shell called `step5_persist_round_start()` for handoffs and deferred the timing row until `step-5-resume.sh --record-only` ran after orchestrator adjudication/application. Because `record_round_timing()` is idempotent when a matching ledger row already exists, `step-5-resume.sh` will skip re-recording and handoff wall-clock time is lost from timing reports and progress surfaces that read `round-start-s`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step5-contract-output.txt: On handoff statuses, persist `round-start-s` and skip the immediate `record_round_timing()` call; only emit the final envelope (and escalation side effects). Let `step-5-resume.sh` record the end timestamp after MAV/CMAR work, matching the old shell contract. Cover with a pytest in the `loop_timing` group.


### FINDING_16: Submodule path normalization mismatch between scrub and revert
- **Reviewer(s)**: dyn-coder-dispatch-output.txt
- **Severity**: important
- **Concern**: `_submodule_paths()` feeds post-dispatch revert and the coder prohibition block but does not normalize submodule roots the way scrub does in `python/redact.py:513-532` (`strip("/")`). When a submodule path is stored with a trailing slash (e.g. `vendor/`), `_post_dispatch_submodule_revert` tests `path.startswith(f"{sub}/")`, which becomes `vendor//` and fails to match `vendor/foo`, so submodule edits may survive revert while scrub thought it had already removed those findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-coder-dispatch-output.txt: Reuse `redact._discover_submodule_paths(Path.cwd())` (or a shared normalized helper) for both scrub and revert/prohibition so submodule roots are byte-identical across layers; add a pytest where `.gitmodules` contains `path = vendor/` and a mocked coder touches `vendor/tracked.txt`, asserting `revert_count > 0` and `CODER_STATUS=submodule-violation`.


### FINDING_2: Loop-mode preflight failures exit without `STEP5_REVIEW_STATUS` envelope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Loop-mode preflight failures return exit `2` without emitting a `STEP5_REVIEW_STATUS` envelope. `/implement` Step 5 background tasks then exit with no parseable status on failures such as empty plan or bad session-env.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Emit structured stall envelope before return on loop-mode preflight failure


### FINDING_3: Invalid `LARCH_DYNAMIC_ARCHETYPES_MAX` crashes Step 5 uncaught
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: An invalid `LARCH_DYNAMIC_ARCHETYPES_MAX` value raises an uncaught `ValueError` inside `_run_round` when session-env is outside `0..3`, crashing Step 5 with a traceback and no final envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Validate in `_preflight_step5` or catch in loop and map to `STEP5_REVIEW_STATUS=stall`


### FINDING_4: `record-escalation` failure omits Tool Failure execution-issues breadcrumb
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When `record-escalation` fails, the code emits fallback ledger KVs but not a Tool Failure execution-issues breadcrumb. Escalation helper failure can leave `execution-issues.md` without `record-escalation` evidence that stall-recovery expects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Append execution-issues Tool Failure block or route through helper degraded-evidence path on failure


### FINDING_5: `python/test_review_and_fix.py` missing priority contract coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The plan lists extensive pytest coverage, but the file has roughly twenty tests and is missing preflight negatives, lint cap, escalation, MAV snapshot, and related cases. Regressions in critical Step 5 contracts can ship because Makefile `-k` subsets do not pin them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port priority harness cases from deleted shell tests per plan acceptance list


### FINDING_8: Makefile `-k` filters match zero pytest tests (exit 5 on CI)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-review-and-fix-record-timing` and `test-review-and-fix-commit-fixes` use pytest `-k` filters that match zero tests; pytest exits `5` on CI shards 3 and 9. Timing and commit-fix contracts appear covered but are not actually exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `@pytest.mark.record_timing` and `@pytest.mark.commit_fixes` tests (or rename tests); register marks in `pyproject.toml`


### FINDING_9: `fix-applied` rounds rewritten to `converged-small-changes` before post-round gates
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `fix-applied` rounds can be rewritten to `converged-small-changes` before the Step 5 loop runs post-round gates. If review core accepts a small non-important finding, the coder applies it, and relevant checks then fail, Step 5 treats the round as complete and skips `_step5_post_round_gates()`, including relevant-checks and lint-fix recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Do not include `fix-applied` in the convergence heuristic. Run the post-round gates first, then complete only after checks and continuation gates pass.


