# Design Outline — Issue #6933

## Goal
Close the parity gap between the shell `gh`-mutation helper and the Python live-mutation authorization so the shell path enforces the same trusted-root containment and run-identity rules as `check_live_mutation_auth`, with a non-circular trusted-root.

## Surfaces (binding scope)
- `scripts/file-failure-report-cross-repo.sh` — `check_mutation_auth`: accept an authoritative `--trusted-root` from the caller and forward it to `session check-live-mutation-auth`; remove the `dirname(context_file)` derivation. Update usage string.
- `python/larch/state/_report.py` — two invokers (`_emit_chat_print_filing_status` ~L493, dedup-tier-a path ~L819): add `--trusted-root str(tmpdir)`.
- `python/larch/design/design_terminal.py` — three fixes: (a) bash-helper invoker ~L884 adds `--trusted-root str(design_tmpdir)`; (b) `_reconcile_post_recovery_comment` L558 add `trusted_root=design_tmpdir`; (c) tier-a dedup pre-check L926 add `trusted_root=design_tmpdir`. The latter two are fail-closed regressions from #6896.
- Tests — `scripts/test-file-failure-report-cross-repo.sh`, `python/tests/state/test_stall_recovery.py`, `python/tests/state/test_session_env.py`, and design_terminal auth coverage; add a negative test confirming a caller-pinned root rejects a context file outside the real session.
- Docs — `scripts/file-failure-report-cross-repo.md`, `python/stall-recovery-report.md`; verify `SECURITY.md` wording (surface set unchanged).

## Non-goals
- No change to `session check-live-mutation-auth` CLI contract or `check_live_mutation_auth` signature.
- No change to authoritative Python callers (`_report.py` pre-checks, `oos_filer.py`, `issue_create.py`, `audit_runs.close-priors` operator gating).
- No new unforgeable-secret / run-id channel; no call-chain-trust-model redesign.
- No refactor of stall-recovery tier filing beyond the auth pin.

## Confirmed audit (no change needed)
- `issue_create.py:559` — callers (`scope_disposition.py:1216`, `oos_filer.py:873`) already pass `--trusted-root tmpdir`. Authoritative.
- `audit_runs.py:1270` — `operator_mode` gated, `context_file=None` by design.
- Only one bash `gh`-mutation surface exists (`file-failure-report-cross-repo.sh`); other `*.sh` hits are test harnesses or non-mutation state machines.
