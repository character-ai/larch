# Review Round 1

- Mode: `diff`
- 18 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: checks lint-fix ignores session-env CODEX_PRESENT/CURSOR_PRESENT
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-checks-port-output.txt
- **Severity**: important
- **Concern**: `checks_lint_fix_main` reads `CODEX_PRESENT` and `CURSOR_PRESENT` only from `os.environ` (lines 1018–1019). `/implement` Steps 3, 5 (self-review), and 6 call `python/cli.py checks lint-fix` without exporting those keys, while `$IMPLEMENT_TMPDIR/session-env.sh` may have them set. External Codex/Cursor fixers are skipped and `main-agent-required` fires despite Step 0 selecting available tools. Step 5’s absorbed loop is unaffected because `review_and_fix._presence_flag` reads session-env.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Read CODEX_PRESENT/CURSOR_PRESENT from IMPLEMENT_TMPDIR/session-env.sh in checks_lint_fix_main (mirror review_and_fix._presence_flag) and add pytest coverage
  - From codex-specialist-correctness-output.txt: Read presence flags from session-env when env vars are unset or invalid
  - From cursor-specialist-edge-cases-output.txt: Read CODEX_PRESENT/CURSOR_PRESENT from session-env.sh (same as deleted lint-fix-loop.sh) or export them before CLI lint-fix
  - From codex-specialist-edge-cases-output.txt: Fall back to $tmpdir/session-env.sh when env vars are unset, matching review_and_fix._presence_flag
  - From dyn-checks-port-output.txt: In `checks_lint_fix_main`, resolve presence the same way as `review_and_fix._presence_flag` (env first, then `session read-key` / parse `$IMPLEMENT_TMPDIR/session-env.sh`), and add a pytest that sets `CODEX_PRESENT=true` only in session-env while env is unset.


### FINDING_10: _direct_targets appends py-lint/py-test before harness targets
- **Reviewer(s)**: dyn-checks-port-output.txt
- **Severity**: important
- **Concern**: For rules with `wants_py_lint` / `wants_py_test`, `_direct_targets` (lines 543–563) appends `py-lint` / `py-test` before the rule’s harness targets. Retired bash appended harness targets first. Because `make` stops on the first failing target, ordering changes which check fails and what gets exercised on Python-only edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-checks-port-output.txt: Match bash ordering: append `rule_targets` first, then conditionally append `py-lint` / `py-test`, and add a routing test that asserts target order for a representative `wants_py_lint` rule such as `python/review_and_fix.py`.


### FINDING_11: _existing_regular_files drops symlink paths
- **Reviewer(s)**: dyn-checks-port-output.txt
- **Severity**: important
- **Concern**: `_existing_regular_files` (lines 411–420) excludes symlinks (`not path.is_symlink()`), while bash kept paths where `[ -f "$f" ]` is true for symlinks to regular files. Pre-commit may run on a smaller file set and miss lint failures on symlinked changed paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-checks-port-output.txt: Treat symlink-to-regular-file paths like bash (`is_file()` without excluding symlinks, or resolve symlinks before the regular-file filter), and add a pytest with a symlinked changed file.


### FINDING_12: missing CLI stdout envelope tests for checks run-relevant and lint-fix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_checks.py` exercises `run_relevant_checks` directly but lacks subprocess or `main()` tests for full success/fail/allow-skip envelopes from `checks run-relevant` and `checks lint-fix`. Orchestrator parsers can break on KV drift while unit tests stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add subprocess or main() tests for full success fail and allow-skip envelopes


### FINDING_13: missing Step 5 integration test for checks wiring
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No integration test verifies `review_and_fix._run_relevant_checks_captured` passes correct `repo_root`, site, and presence flags into `checks.run_*`. Gate tests monkeypatch wrappers so wiring regressions can slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Monkeypatch checks.run_* to record kwargs and assert repo root site and presence wiring


### FINDING_14: missing ship-pr.sh stale-reference test per plan
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_migration_lint.py` lacks a test that `scripts/ship-pr.sh` references are flagged by lint retired-scripts. Ship-pr live-reference carve-out regression is not pinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test that scripts/ship-pr.sh reference is flagged by lint retired-scripts


### FINDING_16: no test that default CLI path never emits RELEVANT_CHECKS_SKIPPED
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No test guards against `checks_run_relevant_main` emitting `RELEVANT_CHECKS_SKIPPED=true` without `--allow-skip`. Reintroduced `skipped=True` could let `/implement` skip checks silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Test checks_run_relevant_main without --allow-skip when result.skipped is true


### FINDING_17: conflict-resolution.md incorrectly labeled retirement stub
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md:803` tells the orchestrator not to invoke `conflict-resolution.md`, calling it a “retirement stub,” but the live Python handoff still depends on it for `caller_kind=ship_pr_pre_push` on exit 4 (`python/ship.py`, `ship-pr-exit-matrix.md`). Following line 803 can skip conflict resolution and re-enter ship with an in-progress rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Replace line 803 with language that matches the exit matrix: orchestrator **must** load and run `conflict-resolution.md` for `caller_kind=ship_pr_pre_push` on exit 4 before re-invoking `step-8-ship.sh`; keep the stub wording only for retired bump sub-procedures (NEVER #2), not the whole file.


### FINDING_18: ship-pr-exit-matrix Exit 0 OOS routing is stale
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: important
- **Concern**: `skills/implement/references/ship-pr-exit-matrix.md:11` Exit 0 branch still routes `OOS_PENDING=true` through Step 9a.1, but the Python driver now stalls OOS with exit 3 and `needs_user_reason=oos-filing` (`python/ship.py:1334-1341`). An orchestrator treating exit 0 as the OOS trigger will never run the OOS pipeline when the driver returns 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Remove or rewrite the Exit 0 `OOS_PENDING` branch to point at exit 3 / `needs_user_reason=oos-filing`, and align `skills/implement/references/oos-pipeline.md:3` so it no longer lists “bash Exit 0” as a primary consumer.


### FINDING_19: stall-recovery escalation guidance references deleted bash SHIP_PR_LEDGER_* KV
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md:871` still names “Step 8+ Python **and bash** ship-pr CI handoffs” and tells the orchestrator to parse `bash SHIP_PR_LEDGER_*` fields. Bash `scripts/ship-pr.sh` is deleted; the Python driver exposes handoff metadata only as JSON `ledger_*` keys. Orchestrators may skip `record-escalation` waiting for KV prefixes that no longer exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Update the escalation owners list to Python-only Step 8+ handoffs and replace `SHIP_PR_LEDGER_*` with the pinned JSON `ledger_ready` / `ledger_site` / `ledger_trigger` / `ledger_step` / `ledger_phase` / `ledger_dispatcher` / `ledger_exit_code` / `ledger_failure_detail_log` contract from `skills/implement/SKILL.md:737`.


### FINDING_2: checks lint-fix CLI handoff contract (ledger fields + exit code)
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `checks_lint_fix_main` (lines 1023–1031) does not emit `LINT_FIX_LEDGER_*` fields when `outcome.ledger_ready` is true, and returns exit code 1 for `LINT_FIX_STATUS=main-agent-required`. The retired `lint-fix-loop.sh` returned 0 for that handoff and emitted the escalation ledger. Callers using `set -e` or expecting ledger fields for stall-recovery can abort or miss escalation metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Emit ledger fields from FixOutcome and return 0 for main-agent-required
  - From codex-specialist-edge-cases-output.txt: Emit the full LINT_FIX_LEDGER_* envelope whenever outcome.ledger_ready is true
  - From codex-specialist-testing-output.txt: Return 0 for main-agent-required envelopes, preserve FAILURE_REASON when present, and add CLI-level status/exit tests.


### FINDING_20: oos-disposition-gate.md stale --resume-phase pr-create wording
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/oos-disposition-gate.md:37` says re-entry after checkpoint exit 0 uses `--resume-phase pr-create`. `step-8-ship.sh` no longer forwards `--resume-phase`; `skills/implement/SKILL.md:769,783` route OOS completion through a plain `step-8-ship.sh` re-invoke. Stale wording can send operators down a dead argv path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Replace `--resume-phase pr-create` with “re-invoke `step-8-ship.sh` without resume-phase; Python reads scoped state internally,” matching `skills/implement/SKILL.md:783`.


### FINDING_3: CODER_LOG_FILE resolves to wrong log path
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `CODER_LOG_FILE` lookup uses `run_parent/codex.log` (lines 1026–1030) instead of the per-run subdirectory where Codex/Cursor actually write logs (`lint-fix-loop/site.xxxx/codex.log`). The CLI omits or misreports the coder log path after a successful external fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Carry the actual coder log path in FixOutcome or resolve the created run_dir


### FINDING_4: STDERR_TAIL_PATH points at checks log, not coder stderr
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When Codex/Cursor dispatch fails, `STDERR_TAIL_PATH` is set from `outcome.ledger_failure_detail_log` (checks log stem) rather than the redacted agent stderr tail the retired bash `lint-fix-loop` surfaced. Operators lose actionable coder stderr on external-fixer failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Set STDERR_TAIL_PATH to coder log stem after write_failed_agent_stderr_tail; keep ledger field separate


### FINDING_5: pre-commit availability checked before eligibility is known
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `run_relevant_checks` requires `pre-commit` on PATH (lines 674–676) before determining whether pre-commit would run. A no-change run with agent-lint available can fail when pre-commit is not installed, despite post-check-only validation being sufficient.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Move pre-commit availability check to immediately before pre-commit run --files


### FINDING_6: deletion-only changes skip direct relevant make targets
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: When changed paths contain only deletions (no existing regular files), the no-regular-files branch (lines 692–704) returns after agent-lint without calling `_direct_targets`. Deleting a mapped file such as `scripts/read-result-env.sh` skips target-specific harnesses like `test-read-result-env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Run direct targets from the full changed-file set before returning from the no-regular-files branch
  - From codex-specialist-testing-output.txt: Compute and run direct targets from changed before returning on no-regular-file paths, require pre-commit only when regular files exist, and add a deletion-only pytest.


### FINDING_7: docs/linting.md references removed make test-lint-fix-loop target
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-checks-port-output.txt
- **Severity**: important
- **Concern**: `docs/linting.md:185` still documents `make test-lint-fix-loop`, but the Makefile target was removed in this branch. Operators following docs get “No rule to make target test-lint-fix-loop”.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Replace with the live pytest checks command or another current target
  - From codex-specialist-edge-cases-output.txt: Update the row to the new pytest command or restore a delegating Make target
  - From cursor-specialist-testing-output.txt: Remove or rewrite row to point at make py-test / pytest coverage only


### FINDING_8: SKILL.md Step 3/6 lint-fix stderr surfacing prose is wrong
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ship-cutover-output.txt
- **Severity**: important
- **Concern**: Steps 3 and 6 failure-repair prose (lines 495, 671) tells the orchestrator to pipe lint-fix stdout back into `python/cli.py checks lint-fix` for stderr surfacing after `surface-lint-fix-stderr-tail.sh` deletion. That is not a valid contract: the first `checks lint-fix` call already emits `STDERR_TAIL_PATH` on stdout. Re-invoking lint-fix can loop, miss tails, or stall recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Parse STDERR_TAIL_PATH from lint-fix KV stdout and read/display that file; remove pipe-to-same-CLI wording
  - From dyn-ship-cutover-output.txt: Change both blocks to: after the first `checks lint-fix` call, parse `STDERR_TAIL_PATH` (and `CODER_LOG_FILE` when present) from its stdout KV envelope and read that path for operator-visible tails; do not re-invoke `checks lint-fix` for surfacing.


