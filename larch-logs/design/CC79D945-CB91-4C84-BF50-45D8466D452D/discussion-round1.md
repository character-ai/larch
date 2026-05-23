## Decision 1: Bucket A — Pre-PR exits (Step 6 / 8 / 9a / 9b)

- **Question**: Which pre-PR `exit_stall` paths should the new waterfall (Cursor→Codex→Claude, 1 try each) attempt to recover from?
- **Resolution**: In scope for waterfall recovery: (a) `create-pr.sh` failure and `write-final-report.sh` failure (`exit_stall 9b`); (b) `run_checks_phase` lint-fix exhaustion after the existing 3 attempts (`exit_stall 6`); (c) `oos-disposition-gate` failure (`exit_stall 9a1`). Out of scope (leave structural-stall intact): `bump-branch-guard` (wrong branch / detached / main on non-forked), `classify-bump.sh` / `apply-bump.sh` / `check-bump-version.sh` failures (`exit_stall 8`). These are tree-invariant or version-state bugs no subagent can fix.
- **Source**: user

## Decision 2: Bucket B — CI watch exits (Step 10 / 12)

- **Question**: Should the new waterfall add another escalation on top of `run_evaluate_failure`'s existing 5-attempt vendor cycle, or treat CI fix as already-handled?
- **Resolution**: Treat CI fix as already-handled — no new escalation layer. BUT introduce a **hard constraint** on whatever vendor/subagent does the fix work: the agent MUST reproduce the failed CI job locally, fix the failure locally, and verify it passes locally BEFORE pushing to CI. No more "push and hope". This applies to all CI fix paths (`run_ci_fix_vendor` for `ci-initial` and `ci-merge`, and any new waterfall paths in Buckets A/C).
- **Source**: user

## Decision 3: Bucket C — Rebase + re-bump exits

- **Question**: Where should the new waterfall apply in `run_rebase_rebump`?
- **Resolution**: After vendor `resolve-conflict` (`launch-cursor-ci.sh` then `launch-codex-ci.sh`) fails for non-bump conflicts, add a Claude-subagent escalation tier before `exit_stall`. The waterfall is Cursor→Codex→Claude, 1 try each. Existing deterministic pre-pass for bump-only conflicts (auto-resolve-changelog, `--ours` for plugin.json/version.go/go.sum) is unchanged. Out of scope: `drop-bump-commit.sh` / `git-force-push.sh` / max-rebases storm-cap / detached HEAD stalls — these are state invariants no subagent can fix.
- **Source**: user

## Decision 4: Bucket D — `exit 5` resume paths (RESUME_PHASE)

- **Question**: Should the three `exit 5` resume paths (`step8_apply_bump_same_version`, `force-push-gate`, `ship-pr-rrr-phase14`) be absorbed into in-script handling, or remain as bail-to-main-agent?
- **Resolution**: Absorb all three into in-script handling. (1) `step8_apply_bump_same_version` (apply-bump produces "origin/main has already bumped to X" or "version regression") — sync local main + re-classify + retry mechanically. (2) `force-push-gate` from `implement-finalize.sh postbump conflict` — run force-push gate mechanically. (3) `ship-pr-rrr-phase14` (non-bump conflict in `run_rebase_rebump`) — handled by the Bucket C waterfall (Cursor→Codex→Claude). Eliminates all three `exit 5` paths.
- **Source**: user

## Decision 5: Bucket E — `exit_stall 12d` after merge attempt

- **Question**: Should any of the `12d` triggers (`policy_denied`, `admin_failed`, catch-all `error`) become subagent-recoverable, or all leave intact?
- **Resolution**: Leave all `12d` triggers intact. Confirmed `merge-pr.sh` already tries `--admin` first by default (lines 316-324), retries plain merge if admin fails, and only emits `admin_failed` when BOTH attempts fail — matching the user's directive ("admin should be applied on first merge attempt; if that fails, go back to main agent"). `policy_denied` only fires with the deliberate `--no-admin-fallback` operator choice. Catch-all `error` after the existing head-divergence + transient-net checks is an exotic residual; no subagent-recoverable path.
- **Source**: user (confirmed against `scripts/merge-pr.sh:316-324`)

## Decision 6: Bucket F — `exit 6` transient network

- **Question**: Should `exit_transient_net` paths become an in-script retry loop with bounded backoff, eliminating the bail entirely?
- **Resolution**: Absorb into in-script retry-with-backoff. Script-internal loop: retry the failing helper up to 3 times with jittered exponential backoff (e.g., 2s/4s/8s, ±25% jitter). Eliminates all `exit 6` bails across `write-final-report.sh`, `create-pr.sh`, `merge-pr.sh` (error/admin_failed with transient signature), `ci-wait` bail-with-transient, `rebase-push.sh`. Total cap around 14s of waiting before the underlying stall path is taken.
- **Source**: user

## Decision 7: Bucket G — `exit 3` needs-user-input

- **Question**: For `ci-wait`'s bail-needs-user reasons (fix-attempts-exhausted, design-flaw, escalate, all-vendors-failed), should the waterfall try one more fix attempt before surfacing to the user?
- **Resolution**: Leave `exit 3` intact — these are genuine user-judgment moments. `fix-attempts-exhausted` means `run_evaluate_failure` already burned 5 vendor attempts; another subagent attempt is unlikely to succeed. `design-flaw`, `escalate`, `all-vendors-failed` are explicit `ci-wait` verdicts. Surfacing to the user is the right call.
- **Source**: user
