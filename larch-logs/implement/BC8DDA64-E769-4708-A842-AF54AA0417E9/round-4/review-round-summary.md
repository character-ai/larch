# Review Round 4

- Mode: `diff`
- 9 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Missing per-round review-scout-manifest run-log flush
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Per-round `review-scout-manifest` run-log flush from absorbed `review-and-fix.sh` was not ported. Dynamic-archetype Step 5 rounds emit scout KVs in `review-core.env`, but implement run logs never get `review-scout-manifest`; the shell wrote this batch every round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: After `review_core_capture` parse scout KVs and best-effort run-log write `review-scout-manifest` on happy and early-terminal paths.


### FINDING_11: skills/review/SKILL.md MAV handoff doc drift
- **Reviewer(s)**: dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: The nested `/review` MAV handoff prose still tells the orchestrator to dispatch `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" review-and-fix step5 --mode mav-apply` and says that is "per `skills/implement/SKILL.md`", but the authoritative MAV branch in `skills/implement/references/step5-review-branches.md:15` uses `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py review-and-fix step5 ... --mode mav-apply`. After deleting the shell launchers, this doc drift can send a resumed `/implement` Step 5 MAV path through a direct `python3` call when `CLAUDE_PLUGIN_ROOT` is unset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-surface-output.txt: Update `skills/review/SKILL.md` to point at `step5-review-branches.md` and the `larch-run.sh` fence shape, matching the implement reference file.


### FINDING_13: Security skipped findings not mirrored to implement-tmpdir aggregate
- **Reviewer(s)**: dyn-coder-dispatch-output.txt
- **Severity**: important
- **Concern**: The Python port drops the shell path that appended coder-`SKIPPED` security blocks into `$IMPLEMENT_TMPDIR/skipped-security-findings.md`. `_process_skipped_findings` only writes per-round `round-N/skipped-findings.security.md` and never mirrors held security skips to the session-level aggregate the deleted `review-and-fix.sh` maintained (~1648–1652 on `main`). Non-security skips still flow to `accumulated-oos.md`; security skips stay local per round, but cross-round security skip audit is weaker and operators lose the single implement-tmpdir ledger `SECURITY.md` describes for held security items.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-coder-dispatch-output.txt: After appending to `skipped_security_file`, mirror non-empty content into `implement_tmpdir / "skipped-security-findings.md"` with the same separator semantics as the old shell, and add pytest coverage that two rounds both contribute to the session aggregate while `accumulated-oos.md` stays free of security blocks.


### FINDING_2: apply_findings does not rehydrate CODEX_PRESENT/CURSOR_PRESENT from session-env
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `apply_findings` does not load `CODEX_PRESENT`/`CURSOR_PRESENT` from session-env before coder dispatch. A degraded `/review` session with both vendors marked `false` in `session-env.sh` can still launch Codex or Cursor when binaries exist on `PATH`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Rehydrate `CODEX_PRESENT` and `CURSOR_PRESENT` from `--session-env-path` in `apply_findings` (mirror step5) and add pytest coverage.


### FINDING_5: .gitleaks.toml allowlist drift after shell-to-Python cutover
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-migration-surface-output.txt, dyn-coder-dispatch-output.txt
- **Severity**: important
- **Concern**: The allowlist description names `python/test_review_and_fix.py`, but the `paths` array still allowlists deleted harnesses (`skills/review-and-fix/scripts/test-review-and-fix.sh` at line 19, `skills/implement/scripts/test-write-rejected-findings.sh` at line 34) and does not add `^python/test_review_and_fix\.py$`. Incomplete stale-reference sweep from the shell-to-Python cutover; can confuse future secret-scan maintenance and leaves the new pytest file without the explicit path allowlist the description claims.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Remove stale path from gitleaks allowlist paths array.
  - From dyn-migration-surface-output.txt: Remove the two deleted harness paths from `paths`, add `^python/test_review_and_fix\.py$`, and keep the description in sync with the path list.


### FINDING_6: No negative test for unresolved RUN_ID preflight
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No negative test for unresolved `RUN_ID` preflight despite plan acceptance and code gate at `review_and_fix.py:1690-1692`. Step 5 could start without the hard `RUN_ID` gate or fail with a weaker error; CI would not catch removal of the preflight check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pytest with all `RUN_ID` sources absent; assert `STEP5_REVIEW_STATUS=stall`, `rc=2`, and no review-core call.


### FINDING_7: Cursor coder path missing auth normalization
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The new Cursor coder path launches `cursor agent` without the auth normalization that the deleted shell path ran via `cursor_launcher_setup_auth_argv` in `scripts/lib-cursor-auth.sh`. Concrete failure: `check-reviewers` can mark Cursor present after trimming a whitespace-padded `CURSOR_API_KEY` in its own process, but Step 5 later inherits the original padded env var and this Python path passes it straight to Cursor, causing auth failure and unnecessary Codex or main-agent fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Reuse or port the Cursor launcher auth setup before `run-external-agent`, including whitespace trim/export and model args parity.


### FINDING_8: commit_fixes uses setdefault for empty session-backed env vars
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `commit_fixes` rehydrates Step 7 token and timing env with `os.environ.setdefault`, which does not replace variables that are present but empty. Concrete failure: if `LARCH_TIMING_LEDGER=""` or `LARCH_TOKEN_SESSION_ID=""` is inherited while `session-env.sh` has real values, the subsequent `timing mark` or `token mark` runs without the session binding that the old shell restored with `-z` checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Replace `setdefault` with `if not os.environ.get(key): os.environ[key] = _session_get(...)` for the session-backed keys before invoking token and timing helpers.


### FINDING_9: Loop-mode handoff branches return non-zero exit on review-core failure
- **Reviewer(s)**: dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: Loop-mode handoff branches (`main-agent-vote-required`, `coder-main-agent-required`) emit the correct `STEP5_REVIEW_STATUS` envelope but then `return result.rc` instead of always exiting `0`. The retired `review-implement-step5-loop.sh` path always `exit 0` on both handoffs regardless of per-round `post_exit`, and `run-step5-review.sh` forwarded that zero exit to `/implement`. Here `_run_round` copies a non-zero `review_core_capture` rc into `RoundResult.rc` (`python/review_and_fix.py:1500-1501`), so a review-core process failure paired with `REVIEW_CORE_STATUS=main-agent-vote-required` makes the Step 5 child exit non-zero even though the orchestrator contract is a normal handoff. That can derail the MAV/CMAR branches in `skills/implement/SKILL.md` and also writes a non-zero `STEP5_REVIEW_LEDGER_EXIT_CODE` via `_record_escalation_if_needed(..., result.rc, ...)`, which the old wrapper also kept at `0` on handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step5-contract-output.txt: On both handoff statuses, emit the envelope and ledger KVs, then `return 0` unconditionally (or pass `review_rc=0` into `_record_escalation_if_needed`). Add a pytest where `RoundResult.rc != 0` but `status="main-agent-vote-required"` and assert process exit `0` plus `STEP5_REVIEW_LEDGER_EXIT_CODE=0`.


