# Review Round 1

- Mode: `diff`
- 32 accepted, 4 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: Teardown cleanup target validation is weaker than bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, dyn-finalize-output.txt
- **Severity**: important
- **Concern**: `python/finalize.py` cleanup validation can allow deleting the wrong tmpdir because it omits bash parity checks for tmpdir basename defaults, session-id matching, and tmp-path guarding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, dyn-finalize-output.txt: Address the concern above.


### FINDING_10: Finalize bash-parity tests are smoke-only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` does not exercise enough `implement-finalize.sh` subprocess/parity cases, so postbump, postmerge, and teardown behavior can drift from bash unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_13: Teardown rename uses PR title instead of live issue title
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Stalled/done rename can corrupt the tracking issue title when the PR title differs from the current GitHub issue title.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_14: Post-create final-summary comment is not refreshed with live PR fields
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-ci-merge-output.txt
- **Severity**: important
- **Concern**: After PR creation, Python does not run `write-final-report.sh --comment-only`, so the tracking issue final summary may retain placeholder or missing PR URL/number fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-ci-merge-output.txt: Address the concern above.


### FINDING_17: Harness pytest pin differs from Python test requirements
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `.github/workflows/requirements-test-harnesses.txt` uses a different pytest version than `python/requirements-test.txt`, so harness and py-test shards can disagree on the same commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_18: Planned finalize unit cases are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize.py` does not cover several plan-listed edge cases such as postbump gates, verify mismatch, session cleanup guard, and rename branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_19: test-merge-parity lacks harness timing wrapper
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The Makefile `test-merge-parity` target omits `scripts/harness-timer.sh`, reducing timing consistency and perf-regression visibility versus related harness targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Postmerge verify mismatch incorrectly stalls and skips terminal state/log writes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-bash-parity-output.txt, dyn-finalize-output.txt
- **Severity**: important
- **Concern**: Python treats verify-main mismatch as `STALLED` after a successful merge, then skips `finalize-state.sh`, post-merge log flush, and final-report updates; bash treats verify mismatch as warning-only and still completes terminal state handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-bash-parity-output.txt, dyn-finalize-output.txt: Address the concern above.


### FINDING_20: ShipResult emission can leak sensitive detail text
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `emit_result` prints and journals raw free-text fields, so CI/GitHub failures can expose tokens or internal URLs in stdout and JSONL journals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_21: finalize-state values are not newline-safe
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `write_finalize_state` does not escape or reject embedded newlines, allowing spoofed keys to alter teardown/stall behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_23: Python ship trust boundary is missing from SECURITY.md
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `LARCH_SHIP_PR_IMPL` was documented without a corresponding `SECURITY.md` update for Python driver stdout/trust-boundary handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_25: Teardown reports cleaned when cleanup was refused/skipped
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `teardown` can return a cleaned status and write cleanup markers even when `cleanup_removed` is false due to a guard/refusal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_27: CI loop counters reset across orchestrator reinvocations
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: `iteration`, `rebase_count`, `fix_attempts`, and `transient_retries` are local to each `run_ship()` invocation, so exit-3/exit-6 handbacks reset bash-compatible caps and can allow unbounded work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.


### FINDING_28: Driver lacks ground-truth phase resume/short-circuiting
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: Reinvocation can repeat checks, postbump, log flushing, and PR prep even when a PR already exists or OOS/CI phases were completed, because Python lacks bash-like persisted/ground-truth phase detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.


### FINDING_29: Post-merge run-log PR number is written in the wrong manifest location
- **Reviewer(s)**: dyn-runlogs-output.txt
- **Severity**: important
- **Concern**: Python writes `pr_number` under `steps_ran` as a string, while bash/audit tooling expect a top-level numeric `pr_number`, so completed Python runs can fail completeness verification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlogs-output.txt: Address the concern above.


### FINDING_3: Postbump lacks full bash guard/gate parity before rebase and push
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-finalize-output.txt
- **Severity**: important
- **Concern**: `finalize.postbump` omits bash branch validation, fork/main carve-outs, checkpoint behavior, and force-push remote-presence gating, so it can rebase or push from the wrong state or prematurely push an absent remote branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-finalize-output.txt: Address the concern above.


### FINDING_30: `cwd=None` can skip pre-push log flush before postbump push
- **Reviewer(s)**: dyn-runlogs-output.txt
- **Severity**: important
- **Concern**: The driver computes `repo_root` but passes raw `cwd` into `finalize.postbump`; when `cwd` is `None`, log refresh can skip while rebase/push proceeds, inverting bash ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlogs-output.txt: Address the concern above.


### FINDING_31: Postmerge manifest recovery does not fail closed like bash
- **Reviewer(s)**: dyn-runlogs-output.txt
- **Severity**: important
- **Concern**: If `manifest.json` is missing mid-run, Python can synthesize a minimal manifest and proceed to `status=done` without bash’s partial recovery marker or report-skip behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlogs-output.txt: Address the concern above.


### FINDING_32: Manifest rewrites drop schema-v2/unknown fields
- **Reviewer(s)**: dyn-runlogs-output.txt
- **Severity**: important
- **Concern**: Python manifest load/update/write paths preserve only a small fixed field set, dropping existing fields such as `skill`, `issue_number`, and `schema_version`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlogs-output.txt: Address the concern above.


### FINDING_33: PR title is not carried into RunContext after ensure_pr
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: After PR creation, the driver updates PR number/URL but not `pr_title`, causing later verify/finalize-state logic to compare against an empty or stale expected title.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_34: Postmerge verify omits local-cleanup sync and bash matching rules
- **Reviewer(s)**: dyn-bash-parity-output.txt, dyn-finalize-output.txt
- **Severity**: important
- **Concern**: Python postmerge switches/deletes locally and compares exact subject equality, but bash pulls main and accepts prefix/PR-suffix matches, so valid squash/admin merges can falsely fail verification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt, dyn-finalize-output.txt: Address the concern above.


### FINDING_35: Pre-PR final-report failures are ignored
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `_write_final_report` ignores subprocess return codes, so Python can create a PR after a report failure that bash would treat as a pre-PR stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_36: Retryable merge results incorrectly advance to postmerge
- **Reviewer(s)**: dyn-ci-merge-output.txt
- **Severity**: important
- **Concern**: When `merge_pr` returns retryable results like `ci_not_ready` or `main_advanced`, Python still enters postmerge cleanup instead of remaining in the CI loop like bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-merge-output.txt: Address the concern above.


### FINDING_37: GOTO-rebase skips bash-equivalent log refresh
- **Reviewer(s)**: dyn-ci-merge-output.txt
- **Severity**: important
- **Concern**: The CI `goto_rebase` path calls only `rebase_and_push`, omitting bash’s pre-rebase run-log refresh/fixup, so pushed CI-fix rebases may miss required log artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-merge-output.txt: Address the concern above.


### FINDING_38: Stalled teardown rename is not gated on open issue state
- **Reviewer(s)**: dyn-finalize-output.txt
- **Severity**: important
- **Concern**: Branch A stalled rename attempts issue rename whenever `stall_tracking` is true, rather than first confirming the tracking issue is still open like bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-output.txt: Address the concern above.


### FINDING_39: Stalled sentinel omits issue URL and timestamp
- **Reviewer(s)**: dyn-finalize-output.txt
- **Severity**: important
- **Concern**: `_write_stalled_sentinel` writes an empty `ISSUE_URL` and omits `TIMESTAMP`, weakening stalled-run recovery compared with bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-output.txt: Address the concern above.


### FINDING_41: CLI lacks `--no-logs-commit`
- **Reviewer(s)**: dyn-runtime-cli-output.txt
- **Severity**: important
- **Concern**: `build_parser()` does not expose the bash Step 8+ `--no-logs-commit` contract, so Python invocations may commit logs despite operator intent unless env is separately set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-cli-output.txt: Address the concern above.


### FINDING_42: argparse defaults can clobber RunContext env fallbacks
- **Reviewer(s)**: dyn-runtime-cli-output.txt
- **Severity**: important
- **Concern**: `_ctx_from_args()` overwrites `RunContext.from_env()` fields with empty argparse defaults, losing alternate env keys like `BRANCH`/`ISSUE`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-cli-output.txt: Address the concern above.


### FINDING_43: Boolean env parsing is inconsistent and too narrow
- **Reviewer(s)**: dyn-runtime-cli-output.txt
- **Severity**: important
- **Concern**: `_env_bool()` only treats `"true"` as true, unlike other runtime helpers that accept `1`, `yes`, and `on`, so log suppression flags can be ignored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-cli-output.txt: Address the concern above.


### FINDING_44: CLI crashes can skip the required JSON envelope
- **Reviewer(s)**: dyn-runtime-cli-output.txt
- **Severity**: important
- **Concern**: `main()` has no broad exception handler, so uncaught exceptions can exit without emitting the single JSON object stdout contract expected by the orchestrator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runtime-cli-output.txt: Address the concern above.


### FINDING_5: Forked CI rebase uses the wrong upstream base
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: CI monitor/goto-rebase paths can rebase forked runs against `origin/main` instead of the upstream base remote, diverging from bash fork handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: CI transient retry budget is never updated
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ci-merge-output.txt
- **Severity**: important
- **Concern**: The CI monitor loop always passes `transient_retries=0`, so blind rerun/transient budgets are effectively reset every monitor iteration instead of being bounded like bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ci-merge-output.txt: Address the concern above.


